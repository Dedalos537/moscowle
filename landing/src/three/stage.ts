import * as THREE from 'three';

export interface SceneController {
  /** Avance de 0 a 1 que da la sección (scroll); cada escena decide qué hace con él. */
  setProgress(p: number): void;
  /** Puntero normalizado de -1 a 1. */
  setPointer(x: number, y: number): void;
  dispose(): void;
}

export interface StageOptions {
  canvas: HTMLCanvasElement;
  reducedMotion: boolean;
  /** Llamado en cada cuadro con el tiempo en segundos; devuelve false si ya no hay nada que animar. */
  frame: (time: number, dt: number) => boolean;
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  onResize?: (width: number, height: number) => void;
}

/**
 * Renderer con buenos modales para celulares modestos: densidad de píxeles acotada, solo dibuja mientras el lienzo
 * está a la vista y la pestaña activa, y con movimiento reducido pinta un único cuadro final.
 */
export function createStage(opts: StageOptions) {
  const { canvas, scene, camera } = opts;
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;

  let visible = false;
  let raf = 0;
  let last = performance.now();
  let start = last;
  let running = false;

  const resize = () => {
    const w = canvas.clientWidth;
    const h = canvas.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    opts.onResize?.(w, h);
    renderOnce();
  };

  const renderOnce = () => renderer.render(scene, camera);

  const loop = (now: number) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const more = opts.frame((now - start) / 1000, dt);
    renderer.render(scene, camera);
    if (more && visible && !document.hidden) raf = requestAnimationFrame(loop);
    else running = false;
  };

  const wake = () => {
    if (opts.reducedMotion) {
      opts.frame(1e4, 1);
      renderOnce();
      return;
    }
    if (running || !visible || document.hidden) return;
    running = true;
    last = performance.now();
    raf = requestAnimationFrame(loop);
  };

  const io = new IntersectionObserver(
    ([entry]) => {
      visible = entry.isIntersecting;
      if (visible) wake();
    },
    { rootMargin: '80px' },
  );
  io.observe(canvas);
  const ro = new ResizeObserver(resize);
  ro.observe(canvas);
  const onVisibility = () => wake();
  document.addEventListener('visibilitychange', onVisibility);

  resize();
  start = performance.now();

  return {
    renderer,
    wake,
    renderOnce,
    dispose() {
      cancelAnimationFrame(raf);
      io.disconnect();
      ro.disconnect();
      document.removeEventListener('visibilitychange', onVisibility);
      renderer.dispose();
    },
  };
}

export function webglAvailable(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') || c.getContext('webgl'));
  } catch {
    return false;
  }
}
