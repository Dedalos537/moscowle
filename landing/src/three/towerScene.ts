import * as THREE from 'three';
import { addDaylight, type BlockColor, type BlockShape, clamp01, easeOutBack, makeBlock } from './blocks';
import { createStage, type SceneController } from './stage';

/** Las cifras del centro como una torre: cada dato es un bloque que cae y se apila cuando la sección entra. */

const PIECES: [BlockShape, BlockColor, number][] = [
  ['rect', 'olive', 1.35],
  ['square', 'cobalt', 1.0],
  ['circle', 'coral', 0.95],
  ['triangle', 'lime', 1.0],
];

export function createTowerScene(canvas: HTMLCanvasElement, reducedMotion: boolean, count: number): SceneController {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  camera.position.set(0, 0.4, 11);
  addDaylight(scene, '#9fb86a');

  const tower = new THREE.Group();
  scene.add(tower);

  const n = Math.max(1, Math.min(count, PIECES.length));
  const step = 1.05;
  const pieces = PIECES.slice(0, n).map(([shape, color, s], i) => {
    const mesh = makeBlock(shape, color, s);
    const restY = -((n - 1) * step) / 2 + i * step;
    // Bloque de pie, de canto hacia la cámara, como apilado sobre una mesa.
    mesh.rotation.set(0, 0.35 * (i % 2 ? -1 : 1), 0);
    tower.add(mesh);
    return { mesh, restY, delay: i * 0.22 };
  });

  let startAt = -1;
  let pendingStart = false;

  const stage = createStage({
    canvas,
    scene,
    camera,
    reducedMotion,
    onResize(w, h) {
      camera.position.z = w / h < 0.8 ? 12.5 : 10.5;
    },
    frame(time) {
      if (pendingStart) {
        startAt = time;
        pendingStart = false;
      }
      if (startAt < 0) {
        pieces.forEach((p) => (p.mesh.position.y = 9));
        return true;
      }
      const t0 = time - startAt;
      let moving = false;
      for (const p of pieces) {
        const t = reducedMotion ? 1 : clamp01((t0 - p.delay) / 0.75);
        p.mesh.position.y = p.restY + (1 - easeOutBack(t)) * 6;
        if (t < 1) moving = true;
      }
      tower.rotation.y = Math.sin(time * 0.35) * 0.25;
      return moving || !reducedMotion;
    },
  });

  let started = false;
  return {
    setProgress(p) {
      // La torre se arma una sola vez, al llegar a la sección.
      if (!started && p > 0) {
        started = true;
        pendingStart = true;
        stage.wake();
      }
    },
    setPointer() {},
    dispose() {
      stage.dispose();
    },
  };
}
