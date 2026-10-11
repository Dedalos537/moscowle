import * as THREE from 'three';

/** Bloques lógicos: el material concreto con el que trabajan las terapeutas, en madera pintada mate. */

export type BlockShape = 'circle' | 'square' | 'triangle' | 'rect';

export const BLOCK_COLORS = {
  lime: '#c4d228',
  olive: '#81a141',
  coral: '#e25f43',
  cobalt: '#2f6fb5',
} as const;

export type BlockColor = keyof typeof BLOCK_COLORS;

function outline(shape: BlockShape): THREE.Shape {
  const s = new THREE.Shape();
  switch (shape) {
    case 'circle':
      s.absarc(0, 0, 0.5, 0, Math.PI * 2, false);
      break;
    case 'triangle': {
      // Esquinas redondeadas: un triángulo de juguete, no una flecha.
      const r = 0.12;
      const pts = [0, 1, 2].map((i) => {
        const a = Math.PI / 2 + (i * Math.PI * 2) / 3;
        return new THREE.Vector2(Math.cos(a) * 0.6, Math.sin(a) * 0.6 - 0.1);
      });
      pts.forEach((p, i) => {
        const prev = pts[(i + 2) % 3];
        const next = pts[(i + 1) % 3];
        const a = p.clone().lerp(prev, r / p.distanceTo(prev));
        const b = p.clone().lerp(next, r / p.distanceTo(next));
        if (i === 0) s.moveTo(a.x, a.y);
        else s.lineTo(a.x, a.y);
        s.quadraticCurveTo(p.x, p.y, b.x, b.y);
      });
      s.closePath();
      break;
    }
    default: {
      const w = shape === 'rect' ? 1.3 : 0.92;
      const h = 0.92 * (shape === 'rect' ? 0.62 : 1);
      const r = 0.1;
      const x = -w / 2;
      const y = -h / 2;
      s.moveTo(x + r, y);
      s.lineTo(x + w - r, y);
      s.quadraticCurveTo(x + w, y, x + w, y + r);
      s.lineTo(x + w, y + h - r);
      s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
      s.lineTo(x + r, y + h);
      s.quadraticCurveTo(x, y + h, x, y + h - r);
      s.lineTo(x, y + r);
      s.quadraticCurveTo(x, y, x + r, y);
    }
  }
  return s;
}

const geometryCache = new Map<BlockShape, THREE.BufferGeometry>();

export function blockGeometry(shape: BlockShape): THREE.BufferGeometry {
  let g = geometryCache.get(shape);
  if (!g) {
    g = new THREE.ExtrudeGeometry(outline(shape), {
      depth: 0.22,
      bevelEnabled: true,
      bevelThickness: 0.06,
      bevelSize: 0.05,
      bevelSegments: 4,
      curveSegments: shape === 'circle' ? 40 : 10,
    });
    g.center();
    geometryCache.set(shape, g);
  }
  return g;
}

const materialCache = new Map<string, THREE.MeshStandardMaterial>();

export function blockMaterial(color: BlockColor | string): THREE.MeshStandardMaterial {
  const hex = color in BLOCK_COLORS ? BLOCK_COLORS[color as BlockColor] : color;
  let m = materialCache.get(hex);
  if (!m) {
    m = new THREE.MeshStandardMaterial({ color: hex, roughness: 0.62, metalness: 0 });
    materialCache.set(hex, m);
  }
  return m;
}

export function makeBlock(shape: BlockShape, color: BlockColor | string, scale = 1): THREE.Mesh {
  const mesh = new THREE.Mesh(blockGeometry(shape), blockMaterial(color));
  mesh.scale.setScalar(scale);
  return mesh;
}

/** Luz de día suave: cielo claro arriba, rebote verde abajo y un sol lateral que marca el bisel. */
export function addDaylight(scene: THREE.Scene, ground = '#3c5a1c'): void {
  scene.add(new THREE.HemisphereLight('#fbfdf3', ground, 1.7));
  const sun = new THREE.DirectionalLight('#fff6e4', 2.1);
  sun.position.set(3, 5, 6);
  scene.add(sun);
  const rim = new THREE.DirectionalLight('#dff0ff', 0.7);
  rim.position.set(-5, -2, 3);
  scene.add(rim);
}

export const easeOutExpo = (t: number) => (t >= 1 ? 1 : 1 - Math.pow(2, -10 * t));
export const easeOutBack = (t: number) => {
  const c1 = 1.4;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
};
export const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
