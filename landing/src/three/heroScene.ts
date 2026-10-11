import * as THREE from 'three';
import { addDaylight, type BlockColor, type BlockShape, clamp01, easeOutBack, makeBlock } from './blocks';
import { createStage, type SceneController } from './stage';

/**
 * Hero: una nube de bloques lógicos. Cada uno flota con su propio periodo, que es la idea de la página: cada niño
 * avanza a su ritmo. Entran escalonados, siguen al puntero (o al dedo) y se abren al hacer scroll.
 */

const LAYOUT: [BlockShape, BlockColor, number, number, number, number][] = [
  // forma, color, x, y, z, escala
  ['circle', 'lime', -0.2, 0.5, 0.6, 1.25],
  ['triangle', 'coral', 1.35, 1.25, -0.4, 1.0],
  ['square', 'cobalt', -1.55, -0.55, -0.2, 1.0],
  ['rect', 'olive', 1.1, -1.0, 0.4, 1.0],
  ['square', 'lime', 0.55, 1.95, -1.4, 0.7],
  ['circle', 'coral', -1.6, 1.4, -1.0, 0.75],
  ['triangle', 'cobalt', 0.15, -1.9, -0.8, 0.8],
  ['circle', 'cobalt', 2.25, 0.15, -1.3, 0.65],
  ['rect', 'coral', -2.4, 0.35, -1.6, 0.75],
  ['triangle', 'lime', -0.95, -1.55, 0.9, 0.62],
  ['square', 'coral', 2.0, -1.85, -1.6, 0.55],
  ['circle', 'olive', 0.85, 0.15, 1.3, 0.48],
  ['rect', 'cobalt', -0.45, 2.25, -2.2, 0.6],
  ['triangle', 'olive', -2.15, -1.7, -2.2, 0.6],
];

function rand(seed: number) {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

export function createHeroScene(canvas: HTMLCanvasElement, reducedMotion: boolean): SceneController {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  camera.position.set(0, 0, 9.5);
  addDaylight(scene, '#2c4214');

  const group = new THREE.Group();
  scene.add(group);

  const blocks = LAYOUT.map(([shape, color, x, y, z, s], i) => {
    const mesh = makeBlock(shape, color, s);
    const home = new THREE.Vector3(x, y, z);
    mesh.position.copy(home);
    mesh.rotation.set(rand(i + 1) * 0.9 - 0.45, rand(i + 7) * 1.2 - 0.6, rand(i + 13) * Math.PI);
    group.add(mesh);
    return {
      mesh,
      home,
      scale: s,
      baseRot: mesh.rotation.clone(),
      // Periodos distintos y no múltiplos entre sí: nunca se sincronizan.
      period: 4.2 + rand(i + 3) * 3.8,
      phase: rand(i + 5) * Math.PI * 2,
      spin: (rand(i + 11) - 0.5) * 0.35,
      delay: 0.08 * i,
      // Al hacer scroll se abren hacia fuera, cada uno en su dirección.
      drift: home.clone().normalize().multiplyScalar(1.4 + rand(i + 17)),
    };
  });

  const pointer = new THREE.Vector2();
  const tilt = new THREE.Vector2();
  let progress = 0;
  let eased = 0;
  let compact = false;

  const stage = createStage({
    canvas,
    scene,
    camera,
    reducedMotion,
    onResize(w, h) {
      // En el celular la escena es una franja ancha: se acerca la cámara para que la nube llene el ancho.
      compact = w / h > 1.25;
      camera.position.z = compact ? 8.2 : w < 520 ? 10.5 : 9.5;
      group.position.x = compact ? 0 : 0.15;
    },
    frame(time, dt) {
      tilt.lerp(pointer, reducedMotion ? 1 : 1 - Math.pow(0.001, dt));
      eased += (progress - eased) * (reducedMotion ? 1 : 1 - Math.pow(0.0005, dt));
      group.rotation.y = tilt.x * 0.28;
      group.rotation.x = -tilt.y * 0.18;

      for (const b of blocks) {
        const t = clamp01((time - b.delay) / 1.1);
        const enter = reducedMotion ? 1 : easeOutBack(t);
        const bob = Math.sin((time / b.period) * Math.PI * 2 + b.phase);
        b.mesh.scale.setScalar(b.scale * Math.max(0.0001, enter));
        b.mesh.position.set(
          b.home.x + b.drift.x * eased,
          b.home.y + bob * 0.16 + b.drift.y * eased + eased * 0.6,
          b.home.z + b.drift.z * eased,
        );
        b.mesh.rotation.set(
          b.baseRot.x + bob * 0.12,
          b.baseRot.y + time * b.spin,
          b.baseRot.z + Math.cos((time / b.period) * Math.PI * 2 + b.phase) * 0.1 + eased * b.spin * 4,
        );
      }
      return true;
    },
  });

  return {
    setProgress(p) {
      progress = clamp01(p);
      stage.wake();
    },
    setPointer(x, y) {
      pointer.set(x, y);
      stage.wake();
    },
    dispose() {
      stage.dispose();
    },
  };
}
