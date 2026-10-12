/*
 * Arranque: renderer, luces, tienda, íconos de productos, bucle principal y puente con Moscowle.
 */
import * as THREE from 'three';
import { PALETTE, PRODUCTS } from './config.js';
import { World } from './world.js';
import { UI } from './ui.js';
import { Audio } from './audio.js';
import { Input } from './input.js';
import { Payment } from './payment.js';
import { Particles } from './fx.js';
import { Wheels } from './actors.js';
import { Game } from './game.js';

const canvas = document.getElementById('c');
const bridge = window.MoscowleGame;
if (bridge) bridge.start('Supermercado');

const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance', alpha: true });
const DPR_CAP = 1.5;
renderer.setPixelRatio(Math.min(devicePixelRatio || 1, DPR_CAP));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFShadowMap;

const scene = new THREE.Scene();
scene.background = new THREE.Color(PALETTE.bg);
scene.fog = new THREE.Fog(PALETTE.bg, 26, 48);

const camera = new THREE.PerspectiveCamera(38, 1, 0.5, 80);

// luz cálida tipo diorama: cielo crema, rebote naranja, sol suave con sombras
const hemi = new THREE.HemisphereLight(0xfff1dc, 0xd99060, 1.25);
scene.add(hemi);
const sun = new THREE.DirectionalLight(0xfff0d8, 2.5);
sun.castShadow = true;
sun.shadow.mapSize.set(1024, 1024);
sun.shadow.camera.left = -11;
sun.shadow.camera.right = 11;
sun.shadow.camera.top = 11;
sun.shadow.camera.bottom = -11;
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 40;
sun.shadow.bias = -0.0006;
sun.shadow.normalBias = 0.03;
sun.shadow.radius = 4;
scene.add(sun, sun.target);
const fill = new THREE.DirectionalLight(0xbfe9ff, 0.45);
fill.position.set(-8, 6, -4);
scene.add(fill);

const world = new World(scene, renderer);
const ui = new UI();
const audio = new Audio();
const input = new Input(canvas);
const payment = new Payment(audio);
const fx = new Particles(scene);
const wheels = new Wheels(scene, world.vcMat);

const game = new Game({ renderer, scene, camera, world, ui, audio, input, payment, fx, wheels, sun });

/* ---------------------------------------------------------------- íconos de productos (renderizados en 3D) */
function renderIcons() {
  const size = 128;
  const iconScene = new THREE.Scene();
  iconScene.add(new THREE.HemisphereLight(0xffffff, 0xd9a070, 2.2));
  const dl = new THREE.DirectionalLight(0xffffff, 1.6);
  dl.position.set(2, 3, 4);
  iconScene.add(dl);
  const cam = new THREE.PerspectiveCamera(30, 1, 0.05, 20);
  const mesh = new THREE.Mesh(undefined, world.productMat);
  iconScene.add(mesh);
  const prevSize = new THREE.Vector2();
  renderer.getSize(prevSize);
  const prevRatio = renderer.getPixelRatio();
  renderer.setPixelRatio(1);
  renderer.setSize(size, size, false);
  renderer.setClearColor(0x000000, 0);
  const prevBg = scene.background;
  const out = document.createElement('canvas');
  out.width = out.height = size;
  const ctx = out.getContext('2d');
  const icons = {};
  const box = new THREE.Box3();
  const c = new THREE.Vector3();
  const sz = new THREE.Vector3();
  for (const p of PRODUCTS) {
    const g = world.geoms[p.id];
    mesh.geometry = g;
    box.copy(g.boundingBox);
    box.getCenter(c);
    box.getSize(sz);
    const r = Math.max(sz.x, sz.y * 1.05, sz.z) * 0.62;
    const dist = r / Math.tan(THREE.MathUtils.degToRad(15)) + 0.05;
    cam.position.set(c.x + dist * 0.28, c.y + dist * 0.32, c.z + dist * 0.9);
    cam.lookAt(c);
    renderer.render(iconScene, cam);
    ctx.clearRect(0, 0, size, size);
    ctx.drawImage(renderer.domElement, 0, 0, size, size);
    icons[p.id] = out.toDataURL('image/png');
  }
  scene.background = prevBg;
  renderer.setClearColor(PALETTE.bg, 1);
  renderer.setPixelRatio(prevRatio);
  renderer.setSize(prevSize.x || innerWidth, prevSize.y || innerHeight, false);
  return icons;
}

/* ---------------------------------------------------------------- tamaño */
function resize() {
  const w = innerWidth;
  const h = innerHeight;
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, DPR_CAP));
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.fov = camera.aspect < 1 ? 46 : 38;
  camera.updateProjectionMatrix();
  ui.layoutTop();
}
addEventListener('resize', resize);

/* ---------------------------------------------------------------- bucle */
let last = performance.now();
let running = true;
let rafId = 0;
const perf = { frames: 0, sum: 0, worst: 0, samples: [] };
window.MarketPerf = {
  reset() {
    perf.frames = 0;
    perf.sum = 0;
    perf.worst = 0;
    perf.samples.length = 0;
  },
  read() {
    const s = perf.samples.slice().sort((a, b) => a - b);
    return {
      frames: perf.frames,
      avgFrameMs: perf.frames ? +(perf.sum / perf.frames).toFixed(2) : 0,
      p95FrameMs: s.length ? +s[Math.floor(s.length * 0.95)].toFixed(2) : 0,
      worstMs: +perf.worst.toFixed(2),
      drawCalls: renderer.info.render.calls,
      triangles: renderer.info.render.triangles,
    };
  },
};

function frame(now) {
  if (!running) return;
  rafId = requestAnimationFrame(frame);
  let dt = (now - last) / 1000;
  last = now;
  if (dt > 0.1) dt = 0.1;
  const t0 = performance.now();
  game.update(dt);
  renderer.render(scene, camera);
  const ms = performance.now() - t0;
  perf.frames++;
  perf.sum += ms;
  if (ms > perf.worst) perf.worst = ms;
  if (perf.samples.length < 2000) perf.samples.push(ms);
}

// sin pestaña visible no se dibuja ni suena nada
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    running = false;
    cancelAnimationFrame(rafId);
    audio.suspend(true);
    if (game.state === 'play') game.pause();
  } else if (!running) {
    running = true;
    last = performance.now();
    audio.suspend(false);
    rafId = requestAnimationFrame(frame);
  }
});

/* ---------------------------------------------------------------- puente con la plataforma */
if (bridge) {
  bridge.onCollect(() => (game.stats.roundsStarted ? game.result() : null));
  addEventListener('pagehide', () => {
    if (game.stats.roundsStarted) bridge.finish(game.result());
  });
}

/* ---------------------------------------------------------------- inicio */
resize();
ui.icons = renderIcons();
resize();
// primer cuadro y precompilación de shaders antes de quitar la pantalla de carga
renderer.compile(scene, camera);
game.updateCamera(0);
renderer.render(scene, camera);
requestAnimationFrame((t) => {
  last = t;
  rafId = requestAnimationFrame(frame);
  setTimeout(() => game.showTitle(), 120);
});
