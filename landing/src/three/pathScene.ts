import * as THREE from 'three';
import { addDaylight, BLOCK_COLORS, clamp01, makeBlock } from './blocks';
import { createStage, type SceneController } from './stage';

/**
 * Recorrido de la evaluación: un bloque lima viaja por un camino con una estación por paso. El scroll de la sección
 * lo mueve; cada estación se enciende al pasar. Es la interacción firma de la página.
 */
export function createPathScene(canvas: HTMLCanvasElement, reducedMotion: boolean, stations: number): SceneController {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
  addDaylight(scene, '#9fb86a');

  const curve = new THREE.CatmullRomCurve3(
    [
      new THREE.Vector3(-3.2, -0.9, 0),
      new THREE.Vector3(-1.7, 0.7, -0.4),
      new THREE.Vector3(-0.2, -0.5, 0.3),
      new THREE.Vector3(1.4, 0.8, -0.2),
      new THREE.Vector3(3.1, -0.3, 0.2),
    ],
    false,
    'centripetal',
  );

  const track = new THREE.Mesh(
    new THREE.TubeGeometry(curve, 160, 0.07, 12, false),
    new THREE.MeshStandardMaterial({ color: '#cddcb0', roughness: 0.8 }),
  );
  scene.add(track);

  // Tramo ya recorrido: el mismo tubo, más grueso y oliva, que se dibuja hasta donde llegó el bloque.
  const doneGeo = new THREE.TubeGeometry(curve, 160, 0.085, 12, false);
  const done = new THREE.Mesh(doneGeo, new THREE.MeshStandardMaterial({ color: BLOCK_COLORS.olive, roughness: 0.6 }));
  scene.add(done);
  const indexPerSegment = 12 * 6;
  const totalSegments = 160;

  const idle = new THREE.Color('#e3ebd0');
  const lit = new THREE.Color(BLOCK_COLORS.olive);
  const stops = Array.from({ length: stations }, (_, i) => (stations === 1 ? 0.5 : i / (stations - 1)));
  const pads = stops.map((t) => {
    const pad = new THREE.Mesh(
      new THREE.CylinderGeometry(0.34, 0.38, 0.08, 40),
      new THREE.MeshStandardMaterial({ color: idle.clone(), roughness: 0.7 }),
    );
    pad.position.copy(curve.getPointAt(t)).add(new THREE.Vector3(0, -0.12, 0));
    scene.add(pad);
    return pad;
  });

  const traveler = makeBlock('circle', 'lime', 0.62);
  scene.add(traveler);

  let target = 0;
  let current = 0;

  const place = (t: number, time: number) => {
    const p = curve.getPointAt(t);
    traveler.position.set(p.x, p.y + 0.3 + Math.abs(Math.sin(time * 3.2)) * (reducedMotion ? 0 : 0.05), p.z);
    // Rueda mientras avanza: el giro sigue a la distancia recorrida.
    traveler.rotation.set(0.25, 0, -t * Math.PI * 6);
    doneGeo.setDrawRange(0, Math.floor(t * totalSegments) * indexPerSegment);
    pads.forEach((pad, i) => {
      const on = clamp01((t - stops[i] + 0.04) / 0.08);
      (pad.material as THREE.MeshStandardMaterial).color.copy(idle).lerp(lit, on);
      pad.scale.setScalar(1 + on * 0.12);
    });
  };

  const stage = createStage({
    canvas,
    scene,
    camera,
    reducedMotion,
    onResize(w, h) {
      // Encuadra el camino entero sea cual sea la proporción del lienzo.
      const fit = Math.max(7.6 / (w / h), 3.4);
      camera.position.set(0, 0.2, fit / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) + 0.6);
      camera.lookAt(0, -0.05, 0);
    },
    frame(time, dt) {
      current += (target - current) * (reducedMotion ? 1 : 1 - Math.pow(0.002, dt));
      place(current, time);
      return reducedMotion ? false : true;
    },
  });

  return {
    setProgress(p) {
      target = clamp01(p);
      stage.wake();
    },
    setPointer() {},
    dispose() {
      stage.dispose();
    },
  };
}
