import * as THREE from 'three';
import { addDaylight, BLOCK_COLORS, type BlockShape, clamp01, easeOutBack } from './blocks';
import { createStage } from './stage';

/**
 * Juego de encaje: un tablero de madera con agujeros. Cada columna es una categoría (su forma) y cada pieza una
 * terapia. Al tocar una pieza sale de su agujero y la sección muestra su información.
 */

export const COLUMN_SHAPES: BlockShape[] = ['circle', 'square', 'triangle', 'rect'];
const ROW_COLORS = [BLOCK_COLORS.coral, BLOCK_COLORS.cobalt, BLOCK_COLORS.olive, BLOCK_COLORS.lime, '#f2a33a'];

export interface SorterController {
  select(col: number, row: number): void;
  setPointer(x: number, y: number): void;
  dispose(): void;
}

const CELL = 1.3;
const PIECE_H = 0.7;
const LIFT = 1.15;

function outline(shape: BlockShape, s: number): THREE.Shape {
  const p = new THREE.Shape();
  if (shape === 'circle') {
    p.absarc(0, 0, 0.42 * s, 0, Math.PI * 2, false);
    return p;
  }
  if (shape === 'triangle') {
    const r = 0.5 * s;
    p.moveTo(-r, -r * 0.82);
    p.lineTo(r, -r * 0.82);
    p.lineTo(-r, r * 0.82);
    p.closePath();
    return p;
  }
  const w = (shape === 'rect' ? 0.98 : 0.8) * s;
  const h = (shape === 'rect' ? 0.56 : 0.8) * s;
  const c = 0.05 * s;
  p.moveTo(-w / 2 + c, -h / 2);
  p.lineTo(w / 2 - c, -h / 2);
  p.quadraticCurveTo(w / 2, -h / 2, w / 2, -h / 2 + c);
  p.lineTo(w / 2, h / 2 - c);
  p.quadraticCurveTo(w / 2, h / 2, w / 2 - c, h / 2);
  p.lineTo(-w / 2 + c, h / 2);
  p.quadraticCurveTo(-w / 2, h / 2, -w / 2, h / 2 - c);
  p.lineTo(-w / 2, -h / 2 + c);
  p.quadraticCurveTo(-w / 2, -h / 2, -w / 2 + c, -h / 2);
  return p;
}

/** Pieza de pie: el contorno extruido hacia arriba, con bisel suave como la madera torneada. */
function pieceGeometry(shape: BlockShape): THREE.BufferGeometry {
  const g = new THREE.ExtrudeGeometry(outline(shape, 1), {
    depth: PIECE_H,
    bevelEnabled: true,
    bevelThickness: 0.05,
    bevelSize: 0.04,
    bevelSegments: 3,
    curveSegments: shape === 'circle' ? 40 : 8,
  });
  g.rotateX(-Math.PI / 2);
  return g;
}

/** Vetas de madera generadas en un canvas: sin descargar imágenes. */
function woodTexture(): THREE.CanvasTexture {
  const c = document.createElement('canvas');
  c.width = 512;
  c.height = 512;
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#d9a866';
  ctx.fillRect(0, 0, 512, 512);
  for (let i = 0; i < 90; i++) {
    const y = Math.random() * 512;
    ctx.strokeStyle = `rgba(${150 + Math.random() * 40}, ${95 + Math.random() * 30}, 45, ${0.08 + Math.random() * 0.14})`;
    ctx.lineWidth = 1 + Math.random() * 3;
    ctx.beginPath();
    ctx.moveTo(0, y);
    for (let x = 0; x <= 512; x += 32) ctx.lineTo(x, y + Math.sin(x / 60 + i) * 4);
    ctx.stroke();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

export function createSorterScene(
  canvas: HTMLCanvasElement,
  reducedMotion: boolean,
  columns: number[],
  onPick: (col: number, row: number) => void,
): SorterController {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 100);
  addDaylight(scene, '#b98d55');

  const cols = columns.length;
  const rows = Math.max(...columns, 1);
  const width = cols * CELL + 0.5;
  const depth = rows * CELL + 0.5;

  const group = new THREE.Group();
  scene.add(group);

  // Tablero
  const wood = woodTexture();
  const boardMat = new THREE.MeshStandardMaterial({ map: wood, roughness: 0.72 });
  const boardShape = new THREE.Shape();
  const r = 0.18;
  const [bw, bd] = [width / 2, depth / 2];
  boardShape.moveTo(-bw + r, -bd);
  boardShape.lineTo(bw - r, -bd);
  boardShape.quadraticCurveTo(bw, -bd, bw, -bd + r);
  boardShape.lineTo(bw, bd - r);
  boardShape.quadraticCurveTo(bw, bd, bw - r, bd);
  boardShape.lineTo(-bw + r, bd);
  boardShape.quadraticCurveTo(-bw, bd, -bw, bd - r);
  boardShape.lineTo(-bw, -bd + r);
  boardShape.quadraticCurveTo(-bw, -bd, -bw + r, -bd);
  const boardGeo = new THREE.ExtrudeGeometry(boardShape, {
    depth: 0.32,
    bevelEnabled: true,
    bevelThickness: 0.04,
    bevelSize: 0.04,
    bevelSegments: 3,
  });
  boardGeo.rotateX(-Math.PI / 2);
  boardGeo.translate(0, -0.32, 0);
  const board = new THREE.Mesh(boardGeo, boardMat);
  group.add(board);

  // Sombra de contacto: un degradado bajo el tablero para que se apoye en una mesa y no flote.
  const sc = document.createElement('canvas');
  sc.width = sc.height = 128;
  const sctx = sc.getContext('2d')!;
  const grad = sctx.createRadialGradient(64, 64, 10, 64, 64, 64);
  grad.addColorStop(0, 'rgba(44, 66, 20, 0.38)');
  grad.addColorStop(1, 'rgba(44, 66, 20, 0)');
  sctx.fillStyle = grad;
  sctx.fillRect(0, 0, 128, 128);
  const shadowTex = new THREE.CanvasTexture(sc);
  const shadow = new THREE.Mesh(
    new THREE.PlaneGeometry(width * 1.5, depth * 1.5),
    new THREE.MeshBasicMaterial({ map: shadowTex, transparent: true, depthWrite: false }),
  );
  shadow.rotation.x = -Math.PI / 2;
  shadow.position.y = -0.4;
  group.add(shadow);

  const holeMat = new THREE.MeshStandardMaterial({ color: '#5a3a1a', roughness: 0.95 });
  const pieceGeos = new Map<BlockShape, THREE.BufferGeometry>();

  interface Piece {
    mesh: THREE.Mesh;
    col: number;
    row: number;
    restY: number;
    lift: number;
    target: number;
    hover: number;
    hoverTarget: number;
    spin: number;
  }
  const pieces: Piece[] = [];

  columns.forEach((count, col) => {
    const shape = COLUMN_SHAPES[col % COLUMN_SHAPES.length];
    if (!pieceGeos.has(shape)) pieceGeos.set(shape, pieceGeometry(shape));
    const x = (col - (cols - 1) / 2) * CELL;
    for (let row = 0; row < count; row++) {
      const z = (row - (rows - 1) / 2) * CELL;
      // Agujero: la silueta oscura un poco más grande, a ras de la tapa.
      const hole = new THREE.Mesh(new THREE.ShapeGeometry(outline(shape, 1.1)), holeMat);
      hole.rotation.x = -Math.PI / 2;
      hole.position.set(x, 0.045, z);
      group.add(hole);

      const mesh = new THREE.Mesh(
        pieceGeos.get(shape)!,
        new THREE.MeshStandardMaterial({ color: ROW_COLORS[row % ROW_COLORS.length], roughness: 0.55 }),
      );
      // Encajada: la base entra en el agujero.
      const restY = -0.22;
      mesh.position.set(x, restY, z);
      mesh.userData = { col, row };
      group.add(mesh);
      pieces.push({ mesh, col, row, restY, lift: 0, target: 0, hover: 0, hoverTarget: 0, spin: 0 });
    }
  });

  // Encuadre a tres cuartos, como la foto del juego.
  const fit = () => {
    const span = Math.max(width, depth);
    camera.position.set(span * 0.95, span * 1.25, span * 1.55);
    camera.lookAt(0, 0.15, 0);
  };

  const raycaster = new THREE.Raycaster();
  const ndc = new THREE.Vector2();
  const hit = (clientX: number, clientY: number): Piece | null => {
    const rect = canvas.getBoundingClientRect();
    ndc.set(((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(ndc, camera);
    const found = raycaster.intersectObjects(pieces.map((p) => p.mesh), false)[0];
    return found ? (pieces.find((p) => p.mesh === found.object) ?? null) : null;
  };

  let selected: Piece | null = null;
  const choose = (p: Piece | null) => {
    if (!p || p === selected) return;
    if (selected) selected.target = 0;
    selected = p;
    p.target = 1;
    stage.wake();
  };

  // Solo un toque cuenta como elección: si el dedo se movió, estaba desplazando la página.
  let down: { x: number; y: number } | null = null;
  const onDown = (e: PointerEvent) => {
    down = { x: e.clientX, y: e.clientY };
  };
  const onClick = (e: PointerEvent) => {
    if (!down || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 10) return;
    down = null;
    const p = hit(e.clientX, e.clientY);
    if (p) {
      choose(p);
      onPick(p.col, p.row);
    }
  };
  let hovered: Piece | null = null;
  const onMove = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    const p = hit(e.clientX, e.clientY);
    if (p === hovered) return;
    if (hovered) hovered.hoverTarget = 0;
    hovered = p;
    if (p) p.hoverTarget = 1;
    canvas.style.cursor = p ? 'pointer' : '';
    stage.wake();
  };
  canvas.addEventListener('pointerdown', onDown);
  canvas.addEventListener('pointerup', onClick);
  canvas.addEventListener('pointermove', onMove);

  const tilt = new THREE.Vector2();
  const pointer = new THREE.Vector2();

  const stage = createStage({
    canvas,
    scene,
    camera,
    reducedMotion,
    onResize: fit,
    frame(time, dt) {
      const k = reducedMotion ? 1 : 1 - Math.pow(0.0008, dt);
      tilt.lerp(pointer, reducedMotion ? 1 : 1 - Math.pow(0.01, dt));
      group.rotation.y = tilt.x * 0.12 + (reducedMotion ? 0 : Math.sin(time * 0.25) * 0.04);
      let moving = false;
      for (const p of pieces) {
        p.lift += (p.target - p.lift) * k;
        p.hover += (p.hoverTarget - p.hover) * k;
        if (Math.abs(p.target - p.lift) > 0.002 || Math.abs(p.hoverTarget - p.hover) > 0.002) moving = true;
        const up = reducedMotion ? p.target : easeOutBack(clamp01(p.lift));
        p.mesh.position.y = p.restY + up * LIFT + p.hover * 0.12;
        // La pieza elegida gira despacio en el aire para que se vea entera.
        if (p.target === 1 && !reducedMotion) p.spin += dt * 0.6;
        else p.spin += (0 - p.spin) * k;
        p.mesh.rotation.y = p.spin;
      }
      return !reducedMotion || moving;
    },
  });

  return {
    select(col, row) {
      choose(pieces.find((p) => p.col === col && p.row === row) ?? null);
    },
    setPointer(x, y) {
      pointer.set(x, y);
      stage.wake();
    },
    dispose() {
      canvas.removeEventListener('pointerdown', onDown);
      canvas.removeEventListener('pointerup', onClick);
      canvas.removeEventListener('pointermove', onMove);
      wood.dispose();
      shadowTex.dispose();
      stage.dispose();
    },
  };
}
