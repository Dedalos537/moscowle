/*
 * La tienda: muebles, letreros, piso, caja registradora y los productos de los estantes.
 * Todo lo estático se fusiona en pocas mallas (colores por vértice + dos atlas) para gastar
 * muy pocas llamadas de dibujo.
 */
import * as THREE from 'three';
import { SECTIONS, PRODUCTS, PRODUCT_BY_ID, STORE, CHECKOUT, COLUMN_W } from './config.js';
import { part, merge, rbox, box, cyl, sph, quad, productGeometry, cartGeometry, wheelGeometry, bagGeometry } from './models.js';
import { buildProductAtlas, buildSignAtlas, buildFloorTexture, buildBeltTexture, buildBlobTexture, buildRingTexture, RegisterScreen } from './textures.js';

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _v = new THREE.Vector3();
const _s = new THREE.Vector3(1, 1, 1);
const _e = new THREE.Euler();
const UP = new THREE.Vector3(0, 1, 0);

const WOOD = 0xc98a52;
const WOOD_D = 0xa86a36;
const SHELF_WHITE = 0xfff6e6;

/** Altura de las repisas (parte superior). */
const GONDOLA_BOARDS = [0.12, 0.6, 1.08];
const FRIDGE_BOARDS = [0.16, 0.64, 1.12];

export class World {
  constructor(scene, renderer) {
    this.scene = scene;
    this.renderer = renderer;
    this.colliders = [];
    this.footprints = [];
    this.columns = [];
    this.static = [];
    this.signs = [];
    this.vcMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.78, metalness: 0 });
    this.productAtlas = buildProductAtlas();
    this.signAtlas = buildSignAtlas();
    this.build();
  }

  addCollider(x0, z0, x1, z1, ao = 0.3, grow) {
    const c = { x0: Math.min(x0, x1), z0: Math.min(z0, z1), x1: Math.max(x0, x1), z1: Math.max(z0, z1) };
    this.colliders.push(c);
    if (ao > 0) this.footprints.push({ ...c, ao, grow });
    return c;
  }

  sign(uv, w, h, pos, rotY = 0) {
    this.signs.push(part(quad(w, h), 0xffffff, { pos, rot: [0, rotY, 0], uv }));
  }

  build() {
    const S = this.static;
    const { x0, x1, z0, z1 } = STORE;
    const W = x1 - x0;
    const D = z1 - z0;
    const cx = (x0 + x1) / 2;
    const cz = (z0 + z1) / 2;

    /* --- base del diorama */
    S.push(part(rbox(W + 0.5, 0.7, D + 2.6, 0.18, 3), 0xe39a55, { pos: [cx, -0.36, cz + 1.05], colorFn: (x, y, z, c) => c.lerp(new THREE.Color(0xb86a2c), THREE.MathUtils.clamp(-y * 1.4, 0, 1)) }));
    // vereda exterior
    S.push(part(rbox(W + 0.2, 0.06, 1.7, 0.03), 0xf3d3a2, { pos: [cx, 0.0, z1 + 1.05] }));
    for (let i = 0; i < 12; i++) S.push(part(box(0.03, 0.065, 1.7), 0xd9b27c, { pos: [x0 + 1 + i * 2, 0.0, z1 + 1.05] }));

    /* --- paredes (norte, oeste, este) */
    const wallH = 2.3;
    const wallC = 0xffe3bd;
    S.push(part(box(W + 0.4, wallH, 0.3), wallC, { pos: [cx, wallH / 2, z0 - 0.15], colorFn: (x, y, z, c) => (y < 0.25 ? c.set(0x8fc4b8) : c) }));
    S.push(part(box(0.3, wallH, D + 0.3), wallC, { pos: [x0 - 0.15, wallH / 2, cz], colorFn: (x, y, z, c) => (y < 0.25 ? c.set(0x8fc4b8) : c) }));
    S.push(part(box(0.3, wallH, D + 0.3), wallC, { pos: [x1 + 0.15, wallH / 2, cz], colorFn: (x, y, z, c) => (y < 0.25 ? c.set(0x8fc4b8) : c) }));
    // cornisa
    S.push(part(rbox(W + 0.6, 0.14, 0.42, 0.05), 0xffd28f, { pos: [cx, wallH + 0.05, z0 - 0.15] }));
    S.push(part(rbox(0.42, 0.14, D + 0.5, 0.05), 0xffd28f, { pos: [x0 - 0.15, wallH + 0.05, cz] }));
    S.push(part(rbox(0.42, 0.14, D + 0.5, 0.05), 0xffd28f, { pos: [x1 + 0.15, wallH + 0.05, cz] }));
    // franjas de color en la pared del fondo
    const stripes = [0x95e7ff, 0xffd28f, 0xd389ff, 0x8fc4b8];
    for (let i = 0; i < 4; i++) S.push(part(box(W * 0.25, 0.12, 0.02), stripes[i], { pos: [x0 + W * (i + 0.5) * 0.25, 1.95, z0 + 0.01] }));
    this.addCollider(x0 - 1, z0 - 1, x1 + 1, z0, 0);
    this.addCollider(x0 - 1, z0 - 1, x0, z1 + 1, 0);
    this.addCollider(x1, z0 - 1, x1 + 1, z1 + 1, 0);
    // borde sur (vereda): no se sale de la tienda
    this.addCollider(x0 - 1, z1 + 0.3, x1 + 1, z1 + 2, 0);

    // letrero grande en la pared del fondo
    this.sign(this.signAtlas.big, 4.4, 1.1, [-1.95, 2.85, z0 + 0.02]);
    S.push(part(rbox(4.5, 1.15, 0.14, 0.12), 0x5b3415, { pos: [-1.95, 2.83, z0 - 0.06] }));
    // reloj
    S.push(part(cyl(0.32, 0.32, 0.06, 24), 0xfff3dc, { pos: [-1.95, 1.45, z0 + 0.03], rot: [Math.PI / 2, 0, 0] }));
    S.push(part(cyl(0.34, 0.34, 0.05, 24), 0xe07a2e, { pos: [-1.95, 1.45, z0 + 0.01], rot: [Math.PI / 2, 0, 0] }));
    S.push(part(box(0.03, 0.2, 0.02), 0x5b3415, { pos: [-1.95, 1.53, z0 + 0.07] }));
    S.push(part(box(0.15, 0.03, 0.02), 0x5b3415, { pos: [-1.88, 1.45, z0 + 0.07] }));
    // afiches
    this.sign(this.signAtlas.posters[1], 0.9, 0.9, [-3.55, 1.2, z0 + 0.03]);
    this.sign(this.signAtlas.posters[2], 0.9, 0.9, [-0.35, 1.2, z0 + 0.03]);
    this.sign(this.signAtlas.posters[0], 1.0, 1.0, [x1 - 0.02, 1.35, -1.5], -Math.PI / 2);
    this.sign(this.signAtlas.posters[1], 1.0, 1.0, [x0 + 0.02, 1.35, -3.0], Math.PI / 2);
    // ventanas laterales
    for (const z of [-6.5, 1.0]) {
      S.push(part(rbox(0.08, 1.0, 1.8, 0.04), 0xfff3dc, { pos: [x0 + 0.02, 1.4, z] }));
      S.push(part(box(0.05, 0.86, 1.66), 0x9fd8ec, { pos: [x0 + 0.05, 1.4, z], colorFn: (x, y, zz, c) => c.lerp(new THREE.Color(0xffffff), THREE.MathUtils.clamp((y - 1.0) * 0.8, 0, 0.6)) }));
      S.push(part(rbox(0.08, 1.0, 1.8, 0.04), 0xfff3dc, { pos: [x1 - 0.02, 1.4, z] }));
      S.push(part(box(0.05, 0.86, 1.66), 0x9fd8ec, { pos: [x1 - 0.05, 1.4, z], colorFn: (x, y, zz, c) => c.lerp(new THREE.Color(0xffffff), THREE.MathUtils.clamp((y - 1.0) * 0.8, 0, 0.6)) }));
    }

    /* --- secciones */
    for (const sec of SECTIONS) {
      if (sec.kind === 'gondola') this.buildGondola(sec);
      else if (sec.kind === 'fridge') this.buildFridge(sec);
      else this.buildStand(sec);
    }

    /* --- decoración */
    this.buildDecor();
    this.buildCheckout();

    /* --- mallas finales */
    const staticMesh = new THREE.Mesh(merge(S), this.vcMat);
    staticMesh.castShadow = true;
    staticMesh.receiveShadow = true;
    staticMesh.matrixAutoUpdate = false;
    this.scene.add(staticMesh);
    this.staticMesh = staticMesh;

    const signMat = new THREE.MeshStandardMaterial({ map: this.signAtlas.tex, vertexColors: true, roughness: 0.6, alphaTest: 0.5 });
    const signMesh = new THREE.Mesh(merge(this.signs), signMat);
    signMesh.receiveShadow = true;
    signMesh.matrixAutoUpdate = false;
    this.scene.add(signMesh);

    // piso con sombra de contacto horneada
    const floorTex = buildFloorTexture(this.footprints);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(W, D), new THREE.MeshStandardMaterial({ map: floorTex, roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2;
    floor.position.set(cx, 0.001, cz);
    floor.receiveShadow = true;
    floor.matrixAutoUpdate = false;
    floor.updateMatrix();
    this.scene.add(floor);

    this.buildArch();
    this.buildProducts();
    this.buildHelpers();
  }

  /* ------------------------------------------------------------ muebles */

  columnX(sec, i) {
    return sec.x0 + (i + 0.5) * COLUMN_W;
  }

  buildGondola(sec) {
    const S = this.static;
    const n = sec.items.length;
    const xa = sec.x0 - 0.06;
    const xb = sec.x0 + n * COLUMN_W + 0.06;
    const w = xb - xa;
    const xm = (xa + xb) / 2;
    const f = sec.z;
    const depth = 0.5;
    const zc = f - depth / 2;
    const col = sec.color;
    const light = new THREE.Color(col).lerp(new THREE.Color(0xffffff), 0.55).getHex();
    S.push(part(rbox(w, 0.14, depth, 0.03), 0x7a4a2a, { pos: [xm, 0.07, zc] }));
    S.push(part(rbox(w, 1.5, 0.08, 0.03), light, { pos: [xm, 0.78, f - depth + 0.04], colorFn: (x, y, z, c) => c.lerp(new THREE.Color(0xffffff), THREE.MathUtils.clamp(y / 1.5, 0, 1) * 0.35) }));
    S.push(part(rbox(0.07, 1.42, depth + 0.04, 0.03), col, { pos: [xa, 0.72, zc] }));
    S.push(part(rbox(0.07, 1.42, depth + 0.04, 0.03), col, { pos: [xb, 0.72, zc] }));
    for (const y of GONDOLA_BOARDS) {
      if (y < 0.2) {
        S.push(part(box(w - 0.06, 0.02, depth - 0.04), SHELF_WHITE, { pos: [xm, 0.13, zc] }));
        continue;
      }
      S.push(part(rbox(w - 0.06, 0.04, depth - 0.02, 0.012), SHELF_WHITE, { pos: [xm, y - 0.02, zc] }));
      S.push(part(rbox(w - 0.04, 0.07, 0.03, 0.012), col, { pos: [xm, y - 0.025, f - 0.005] }));
    }
    // copete superior y letrero de sección
    S.push(part(rbox(w + 0.06, 0.1, depth + 0.06, 0.04), col, { pos: [xm, 1.52, zc] }));
    this.signHeader(sec, xm, 1.58, f - depth + 0.08);
    this.addColumns(sec, GONDOLA_BOARDS, f, 'shelf');
    this.addCollider(xa - 0.04, f - depth - 0.04, xb + 0.04, f + 0.04, 0.42, 0.22);
  }

  signHeader(sec, x, y, z) {
    const w = 2.3;
    const h = 0.72;
    this.static.push(part(cyl(0.025, 0.025, 0.3, 8), 0x5b3415, { pos: [x - 0.7, y + 0.1, z] }));
    this.static.push(part(cyl(0.025, 0.025, 0.3, 8), 0x5b3415, { pos: [x + 0.7, y + 0.1, z] }));
    this.sign(this.signAtlas.headers[sec.id], w, h, [x, y + 0.5, z + 0.03]);
    this.static.push(part(rbox(w * 0.97, h * 0.92, 0.05, 0.05), 0x5b3415, { pos: [x, y + 0.49, z - 0.005] }));
  }

  buildFridge(sec) {
    const S = this.static;
    const n = sec.items.length;
    const xa = sec.x0 - 0.08;
    const xb = sec.x0 + n * COLUMN_W + 0.08;
    const w = xb - xa;
    const xm = (xa + xb) / 2;
    const f = sec.z;
    const depth = 0.85;
    const zc = f - depth / 2;
    const H = 1.75;
    // cuerpo
    S.push(part(rbox(w + 0.12, 0.2, depth, 0.04), 0xf2f6fa, { pos: [xm, 0.1, zc] }));
    S.push(part(box(w, H, 0.08), 0xc9f3ff, { pos: [xm, H / 2, f - depth + 0.04], colorFn: (x, y, z, c) => c.lerp(new THREE.Color(0xffffff), THREE.MathUtils.clamp((y - 0.4) / 1.4, 0, 1) * 0.6) }));
    S.push(part(rbox(0.12, H + 0.1, depth, 0.04), 0xf2f6fa, { pos: [xa, (H + 0.1) / 2, zc] }));
    S.push(part(rbox(0.12, H + 0.1, depth, 0.04), 0xf2f6fa, { pos: [xb, (H + 0.1) / 2, zc] }));
    S.push(part(rbox(w + 0.24, 0.24, depth + 0.06, 0.06), sec.color, { pos: [xm, H + 0.06, zc] }));
    // luz fría superior
    S.push(part(box(w - 0.1, 0.03, 0.06), 0xffffff, { pos: [xm, H - 0.08, f - 0.12] }));
    // separadores entre columnas
    for (let i = 1; i < n; i++) S.push(part(box(0.025, H - 0.2, depth - 0.12), 0xe2f2f8, { pos: [sec.x0 + i * COLUMN_W, H / 2 + 0.05, zc - 0.04] }));
    for (const y of FRIDGE_BOARDS) {
      S.push(part(rbox(w - 0.04, 0.035, depth - 0.1, 0.01), 0xe8f6fb, { pos: [xm, y - 0.018, zc - 0.03] }));
      S.push(part(rbox(w - 0.04, 0.06, 0.03, 0.01), sec.color, { pos: [xm, y - 0.02, f - 0.06] }));
    }
    this.signHeader(sec, xm, H + 0.18, f - depth + 0.15);
    this.addColumns(sec, FRIDGE_BOARDS, f - 0.06, 'fridge');
    this.addCollider(xa - 0.06, f - depth - 0.4, xb + 0.06, f + 0.04, 0.38, 0.2);
  }

  buildStand(sec) {
    const S = this.static;
    const n = sec.items.length;
    const xa = sec.x0 - 0.1;
    const xb = sec.x0 + n * COLUMN_W + 0.1;
    const w = xb - xa;
    const xm = (xa + xb) / 2;
    const f = sec.z;
    const depth = 0.95;
    const zc = f - depth / 2;
    const tilt = 0.32;
    // mesa de madera
    S.push(part(rbox(w, 0.46, depth, 0.05), WOOD_D, { pos: [xm, 0.23, zc], colorFn: (x, y, z, c) => (Math.abs(Math.sin(y * 40)) > 0.92 ? c.multiplyScalar(0.85) : c) }));
    // respaldo con letrero
    S.push(part(rbox(w, 0.35, 0.1, 0.04), WOOD, { pos: [xm, 0.9, f - depth + 0.03] }));
    for (const px of [xa + 0.15, xb - 0.15]) S.push(part(cyl(0.04, 0.04, 1.3, 8), WOOD_D, { pos: [px, 1.1, f - depth + 0.03] }));
    S.push(part(rbox(w * 0.45, 0.1, 0.1, 0.04), WOOD_D, { pos: [xm, 1.6, f - depth + 0.03] }));
    this.signHeader(sec, xm, 1.62, f - depth + 0.05);
    // cajones inclinados
    this.standTilt = tilt;
    for (let i = 0; i < n; i++) {
      const x = this.columnX(sec, i);
      const yc = 0.58;
      S.push(
        part(rbox(COLUMN_W - 0.08, 0.16, depth - 0.12, 0.03), WOOD, {
          pos: [x, yc, zc + 0.02],
          rot: [tilt, 0, 0],
          colorFn: (xx, y, z, c) => (Math.abs(Math.sin((z + y) * 26)) > 0.9 ? c.multiplyScalar(0.82) : c),
        }),
      );
      // cartelito de precio en el borde del cajón
      this.sign(this.signAtlas.tags[sec.items[i]], 0.36, 0.18, [x, 0.53, f + 0.02], 0);
    }
    this.addColumns(sec, null, f, 'stand');
    this.addCollider(xa - 0.04, f - depth - 0.06, xb + 0.04, f + 0.04, 0.4, 0.22);
  }

  /**
   * Crea las columnas (un tipo de producto cada una) y las posiciones de sus unidades.
   * boards=null → cajón inclinado de frutas.
   */
  addColumns(sec, boards, front, kind) {
    sec.items.forEach((pid, i) => {
      const x = this.columnX(sec, i);
      const p = PRODUCT_BY_ID[pid];
      const slots = [];
      const seed = (i + 1) * 7.13 + pid.length;
      const jit = (k) => Math.sin(seed * 12.9898 + k * 78.233) * 0.5;
      if (boards) {
        // cartelitos de precio en la repisa central e inferior
        const tagY = kind === 'fridge' ? boards[1] - 0.06 : boards[1] - 0.05;
        this.sign(this.signAtlas.tags[pid], 0.3, 0.15, [x, tagY, front + 0.03]);
        this.sign(this.signAtlas.tags[pid], 0.3, 0.15, [x, boards[2] - 0.05, front + 0.03]);
        for (let b = 2; b >= 0; b--) {
          for (let k = -1; k <= 1; k++) {
            slots.push({
              pos: new THREE.Vector3(x + k * 0.31 + jit(b * 3 + k) * 0.02, boards[b] + 0.0, front - 0.2 + jit(k + 9) * 0.02),
              rotY: jit(b * 5 + k * 3) * 0.22,
              rotX: 0,
              taken: false,
              id: -1,
            });
          }
        }
      } else {
        const tilt = this.standTilt;
        const fruitRot = p.shape === 'banana' || p.shape === 'corn' ? 0.5 : 1.4;
        for (let r = 0; r < 2; r++) {
          for (let k = -1; k <= 1; k++) {
            const d = 0.24 + r * 0.3;
            slots.push({
              pos: new THREE.Vector3(x + k * 0.27 + jit(r * 3 + k) * 0.04, 0.6 + d * Math.sin(tilt) * 1.05 + 0.02, front - 0.06 - d * Math.cos(tilt)),
              rotY: jit(r * 7 + k) * fruitRot,
              rotX: tilt,
              taken: false,
              id: -1,
            });
          }
        }
      }
      // las unidades se toman de adelante hacia atrás y de arriba hacia abajo
      const col = {
        index: this.columns.length,
        sec: sec.id,
        productId: pid,
        product: p,
        x,
        front,
        kind,
        slots,
        top: boards ? boards[2] + 0.45 : 1.25,
        box: new THREE.Box3(new THREE.Vector3(x - 0.5, 0, front - 0.6), new THREE.Vector3(x + 0.5, boards ? boards[2] + 0.4 : 1.0, front + 0.12)),
      };
      this.columns.push(col);
    });
  }

  buildDecor() {
    const S = this.static;
    const plant = (x, z, s = 1) => {
      S.push(part(cyl(0.22 * s, 0.17 * s, 0.38 * s, 14), 0xe07a2e, { pos: [x, 0.19 * s, z], colorFn: (xx, y, zz, c) => (y > 0.32 * s ? c.set(0xffd28f) : c) }));
      S.push(part(sph(0.3 * s, 12, 10), 0x5aa83a, { pos: [x, 0.62 * s, z], colorFn: (xx, y, zz, c) => c.lerp(new THREE.Color(0x8fd16a), THREE.MathUtils.clamp((y - 0.5 * s) * 2, 0, 1)) }));
      S.push(part(sph(0.22 * s, 10, 8), 0x6cbf4a, { pos: [x + 0.16 * s, 0.84 * s, z + 0.05], colorFn: (xx, y, zz, c) => c.lerp(new THREE.Color(0x9fe07a), 0.3) }));
      S.push(part(sph(0.2 * s, 10, 8), 0x4f9a3a, { pos: [x - 0.15 * s, 0.86 * s, z - 0.05] }));
      this.addCollider(x - 0.26 * s, z - 0.26 * s, x + 0.26 * s, z + 0.26 * s, 0.3, 0.12);
    };
    plant(STORE.x0 + 0.5, STORE.z0 + 0.6, 1.1);
    plant(STORE.x1 - 0.5, STORE.z0 + 0.6, 1.1);
    plant(-0.65, STORE.z0 + 0.5, 0.9);
    plant(STORE.x1 - 0.5, 7.9, 1);
    plant(-3.0, 8.0, 0.9);

    // corral de carritos junto a la entrada
    const cg = cartGeometry(0x95e7ff, 0xffd28f);
    const wg = wheelGeometry();
    for (let i = 0; i < 2; i++) {
      const g = cg.clone();
      g.rotateY(-Math.PI / 2);
      g.translate(-10.6 + i * 0.32, 0.06, 6.9);
      S.push(g);
      for (const [wx, wz] of [[0.25, 0.2], [-0.25, 0.2], [0.25, -0.2], [-0.25, -0.2]]) {
        const w = wg.clone();
        w.rotateY(-Math.PI / 2);
        w.translate(-10.6 + i * 0.32 + wz, 0.06, 6.9 + wx);
        S.push(w);
      }
    }
    S.push(part(rbox(1.6, 0.08, 1.0, 0.03), 0x9aa0ad, { pos: [-10.45, 0.6, 6.9] }));
    this.addCollider(-11.4, 6.25, -9.6, 7.55, 0.3);

    // isla de ofertas (pirámide de latas y cajas)
    const ox = 8.9;
    const oz = -2.9;
    S.push(part(rbox(1.6, 0.18, 1.2, 0.04), WOOD_D, { pos: [ox, 0.09, oz] }));
    const canC = [0xe63946, 0xffb22e, 0x2bb673];
    let k = 0;
    for (let row = 0; row < 3; row++) {
      for (let i = 0; i < 4 - row; i++) {
        for (let j = 0; j < 3 - row; j++) {
          const c = canC[(k++) % 3];
          S.push(part(cyl(0.12, 0.12, 0.24, 14), c, { pos: [ox - 0.42 + row * 0.14 + i * 0.28, 0.3 + row * 0.25, oz - 0.3 + row * 0.14 + j * 0.28], colorFn: (x, y, z, cc) => (Math.abs(y - (0.3 + row * 0.25)) > 0.09 ? cc.set(0xd8dce4) : cc) }));
        }
      }
    }
    S.push(part(cyl(0.025, 0.025, 1.3, 8), 0x5b3415, { pos: [ox + 0.7, 0.8, oz + 0.5] }));
    this.sign(this.signAtlas.posters[0], 0.8, 0.8, [ox + 0.7, 1.55, oz + 0.53]);
    this.addCollider(ox - 0.85, oz - 0.65, ox + 0.85, oz + 0.65, 0.35);

    // pila de cajas de cartón junto a abarrotes
    for (const [bx, by, bz, r] of [[-1.6, 0.25, -3.8, 0.1], [-1.55, 0.72, -3.82, -0.12], [-1.15, 0.25, -3.6, 0.3]]) {
      S.push(part(rbox(0.5, 0.48, 0.5, 0.04), 0xd9a066, { pos: [bx, by, bz], rot: [0, r, 0] }));
      S.push(part(box(0.51, 0.06, 0.12), 0xc48748, { pos: [bx, by + 0.215, bz], rot: [0, r, 0] }));
    }
    this.addCollider(-1.95, -4.15, -0.85, -3.3, 0.3);

    // globos en la entrada
    const bal = [0xd389ff, 0x95e7ff, 0xffd28f, 0xe63946];
    bal.forEach((c, i) => {
      const bx = -8.9 + i * 0.22;
      const by = 2.75 + (i % 2) * 0.25;
      S.push(part(sph(0.2, 14, 10), c, { pos: [bx, by, 8.6], scale: [1, 1.18, 1], colorFn: (x, y, z, cc) => cc.lerp(new THREE.Color(0xffffff), THREE.MathUtils.clamp((y - by) * 2.2, 0, 0.45)) }));
      S.push(part(cyl(0.006, 0.006, 0.6, 4), 0xfff3dc, { pos: [bx * 0.5 + -8.65 * 0.5, by - 0.48, 8.6], rot: [0, 0, (bx + 8.65) * 0.7] }));
    });

    // exterior: árboles y banca
    const tree = (x, z, s) => {
      S.push(part(cyl(0.08 * s, 0.11 * s, 0.9 * s, 8), 0x8a5a2b, { pos: [x, 0.45 * s, z] }));
      S.push(part(sph(0.55 * s, 12, 10), 0x6cbf4a, { pos: [x, 1.15 * s, z], colorFn: (xx, y, zz, c) => c.lerp(new THREE.Color(0xb6e86a), THREE.MathUtils.clamp((y - 1.1 * s) * 1.6, 0, 0.6)) }));
      S.push(part(sph(0.38 * s, 10, 8), 0x58ab3c, { pos: [x + 0.35 * s, 0.95 * s, z + 0.1] }));
    };
    tree(STORE.x0 + 0.9, STORE.z1 + 1.15, 0.9);
    tree(STORE.x1 - 0.8, STORE.z1 + 1.1, 1.0);
    tree(1.6, STORE.z1 + 1.2, 0.75);
    S.push(part(rbox(1.3, 0.08, 0.4, 0.03), WOOD, { pos: [-2.0, 0.42, STORE.z1 + 1.15] }));
    S.push(part(rbox(1.3, 0.3, 0.06, 0.03), WOOD, { pos: [-2.0, 0.62, STORE.z1 + 1.35] }));
    for (const lx of [-2.5, -1.5]) S.push(part(box(0.06, 0.4, 0.34), 0x5b3415, { pos: [lx, 0.2, STORE.z1 + 1.15] }));
  }

  buildArch() {
    // arco de entrada: se vuelve translúcido cuando tapa al jugador
    const parts = [];
    const ax = -6.6;
    const az = STORE.z1 - 0.15;
    for (const dx of [-2.0, 2.0]) {
      parts.push(part(rbox(0.32, 2.5, 0.32, 0.08), 0x8fc4b8, { pos: [ax + dx, 1.25, az] }));
      parts.push(part(rbox(0.42, 0.18, 0.42, 0.06), 0xffd28f, { pos: [ax + dx, 0.09, az] }));
    }
    parts.push(part(rbox(4.5, 0.32, 0.36, 0.1), 0x8fc4b8, { pos: [ax, 2.55, az] }));
    this.archMat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.75, transparent: true, opacity: 1 });
    const arch = new THREE.Mesh(merge(parts), this.archMat);
    arch.castShadow = true;
    this.scene.add(arch);
    const sMat = new THREE.MeshStandardMaterial({ map: this.signAtlas.tex, transparent: true, roughness: 0.6, alphaTest: 0.02 });
    this.archSignMat = sMat;
    const s = new THREE.Mesh(part(quad(1.9, 0.6), 0xffffff, { pos: [ax, 2.58, az + 0.19], uv: this.signAtlas.entrada }), sMat);
    this.scene.add(s);
    this.arch = { mesh: arch, x: ax, z: az, alpha: 1 };
    this.addCollider(ax - 2.2, az - 0.2, ax - 1.8, az + 0.2, 0);
    this.addCollider(ax + 1.8, az - 0.2, ax + 2.2, az + 0.2, 0);
  }

  updateArch(px, pz, dt) {
    const a = this.arch;
    const near = pz < a.z && pz > a.z - 3.6 && Math.abs(px - a.x) < 3.2;
    const target = near ? 0 : 1;
    a.alpha += (target - a.alpha) * (1 - Math.exp(-10 * dt));
    if (Math.abs(a.alpha - target) < 0.02) a.alpha = target;
    a.mesh.visible = a.alpha > 0.01;
    this.archMat.opacity = a.alpha;
    this.archMat.depthWrite = a.alpha > 0.95;
    this.archSignMat.opacity = a.alpha;
  }

  /* ------------------------------------------------------------ caja */

  buildCheckout() {
    const S = this.static;
    const { counterX, z0, z1 } = CHECKOUT;
    const len = z1 - z0;
    const zm = (z0 + z1) / 2;
    const cw = 0.9;
    // mostrador
    S.push(part(rbox(cw, 0.8, len, 0.08, 3), 0x8fc4b8, { pos: [counterX, 0.4, zm], colorFn: (x, y, z, c) => (y > 0.66 ? c.set(0xfff3dc) : y < 0.1 ? c.set(0x5b8f84) : c) }));
    S.push(part(rbox(cw + 0.04, 0.05, len + 0.04, 0.02), 0xfff3dc, { pos: [counterX, 0.81, zm] }));
    // marco de la cinta
    S.push(part(box(0.06, 0.06, len * 0.62), 0x9aa0ad, { pos: [counterX - 0.31, 0.875, z0 + len * 0.31 + 0.1] }));
    S.push(part(box(0.06, 0.06, len * 0.62), 0x9aa0ad, { pos: [counterX + 0.31, 0.875, z0 + len * 0.31 + 0.1] }));
    // escáner
    const scanZ = z0 + len * 0.68;
    this.scanZ = scanZ;
    S.push(part(rbox(0.62, 0.05, 0.45, 0.02), 0x3b3340, { pos: [counterX, 0.84, scanZ] }));
    S.push(part(box(0.4, 0.02, 0.3), 0x5ad1ff, { pos: [counterX, 0.865, scanZ], colorFn: (x, y, z, c) => c.lerp(new THREE.Color(0xffffff), 0.2) }));
    S.push(part(rbox(0.42, 0.32, 0.08, 0.03), 0x3b3340, { pos: [counterX + 0.12, 1.0, scanZ - 0.24] }));
    // zona de bolsas
    S.push(part(rbox(cw - 0.06, 0.04, 1.0, 0.02), 0xd8dce4, { pos: [counterX, 0.83, z1 - 0.55] }));
    // registradora
    const rx = counterX + 0.32;
    const rz = scanZ - 0.75;
    S.push(part(cyl(0.04, 0.05, 0.4, 10), 0x9aa0ad, { pos: [rx, 1.0, rz] }));
    S.push(part(rbox(0.5, 0.2, 0.4, 0.05), 0xfff3dc, { pos: [rx + 0.05, 0.92, rz] }));
    S.push(part(rbox(0.46, 0.34, 0.08, 0.04), 0x5b3415, { pos: [rx, 1.32, rz], rot: [0, -0.6, 0] }));
    this.registerPos = new THREE.Vector3(rx, 1.32, rz);
    // poste con letrero CAJA
    S.push(part(cyl(0.04, 0.04, 1.6, 10), 0x5b3415, { pos: [counterX + 0.38, 1.6, z0 + 0.25] }));
    this.sign(this.signAtlas.caja, 1.3, 0.54, [counterX + 0.38, 2.55, z0 + 0.31]);
    S.push(part(rbox(1.3, 0.5, 0.06, 0.06), 0x5b3415, { pos: [counterX + 0.38, 2.54, z0 + 0.26] }));
    this.addCollider(counterX - cw / 2 - 0.04, z0 - 0.04, counterX + cw / 2 + 0.04, z1 + 0.04, 0.35);
    // caja cerrada al lado
    const c2 = counterX + 3.0;
    S.push(part(rbox(cw, 0.8, len, 0.08, 3), 0xd9a8ff, { pos: [c2, 0.4, zm], colorFn: (x, y, z, c) => (y > 0.66 ? c.set(0xfff3dc) : y < 0.1 ? c.set(0x9a6cc7) : c) }));
    S.push(part(rbox(cw + 0.04, 0.05, len + 0.04, 0.02), 0xfff3dc, { pos: [c2, 0.81, zm] }));
    S.push(part(cyl(0.04, 0.04, 1.6, 10), 0x5b3415, { pos: [c2 + 0.38, 1.6, z0 + 0.25] }));
    this.sign(this.signAtlas.closed, 1.3, 0.54, [c2 + 0.38, 2.55, z0 + 0.31]);
    S.push(part(rbox(1.3, 0.5, 0.06, 0.06), 0x5b3415, { pos: [c2 + 0.38, 2.54, z0 + 0.26] }));
    // cadena
    for (let i = 0; i < 7; i++) S.push(part(sph(0.035, 6, 5), 0xffb22e, { pos: [c2 - 0.6 - i * 0.15 * 0.0, 0.7 - Math.sin((i / 6) * Math.PI) * 0.15, z0 + 0.1 + i * 0.0] }));
    this.addCollider(c2 - cw / 2 - 0.04, z0 - 0.04, c2 + cw / 2 + 0.04, z1 + 0.04, 0.35);
    // separador entre carriles
    S.push(part(rbox(0.12, 0.9, 1.6, 0.05), 0xffd28f, { pos: [counterX + 1.5, 0.45, z1 - 0.7] }));
    this.addCollider(counterX + 1.42, z1 - 1.5, counterX + 1.58, z1 + 0.1, 0.25);

    // cinta transportadora (textura que se desplaza)
    this.beltTex = buildBeltTexture();
    this.beltTex.repeat.set(1, len * 0.62 * 3);
    const belt = new THREE.Mesh(new THREE.PlaneGeometry(0.56, len * 0.62), new THREE.MeshStandardMaterial({ map: this.beltTex, roughness: 0.6 }));
    belt.rotation.x = -Math.PI / 2;
    belt.position.set(counterX, 0.848, z0 + len * 0.31 + 0.1);
    belt.receiveShadow = true;
    this.scene.add(belt);
    this.beltStart = new THREE.Vector3(counterX, 0.85, z0 + 0.4);
    this.beltEnd = new THREE.Vector3(counterX, 0.85, scanZ - 0.3);
    this.scanPos = new THREE.Vector3(counterX, 0.9, scanZ);
    this.bagPos = new THREE.Vector3(counterX, 0.85, z1 - 0.5);

    // pantalla de la registradora
    this.register = new RegisterScreen();
    const screen = new THREE.Mesh(new THREE.PlaneGeometry(0.4, 0.2), new THREE.MeshBasicMaterial({ map: this.register.tex, toneMapped: false }));
    screen.position.set(rx + Math.sin(-0.6) * 0.045, 1.33, rz + Math.cos(-0.6) * 0.045);
    screen.rotation.y = -0.6;
    this.scene.add(screen);

    // láser del escáner
    this.laser = new THREE.Mesh(new THREE.PlaneGeometry(0.42, 0.02), new THREE.MeshBasicMaterial({ color: 0xff3355, transparent: true, opacity: 0, toneMapped: false }));
    this.laser.rotation.x = -Math.PI / 2;
    this.laser.position.set(counterX, 0.88, scanZ);
    this.scene.add(this.laser);

    // bolsa
    this.bag = new THREE.Mesh(bagGeometry(), this.vcMat);
    this.bag.position.copy(this.bagPos);
    this.bag.castShadow = true;
    this.bag.scale.setScalar(0.001);
    this.bag.visible = false;
    this.scene.add(this.bag);
  }

  /* ------------------------------------------------------------ productos */

  buildProducts() {
    const mat = new THREE.MeshStandardMaterial({ map: this.productAtlas.tex, vertexColors: true, roughness: 0.55, metalness: 0 });
    this.productMat = mat;
    this.geoms = {};
    for (const p of PRODUCTS) this.geoms[p.id] = productGeometry(p, this.productAtlas.uvs);
    /*
     * Una InstancedMesh por tipo de producto (≈38 llamadas de dibujo, funciona igual en iPad sin multi-draw).
     * Cada unidad del estante es una instancia; al tomarla, esa misma instancia vuela al carrito,
     * pasa por la caja y vuelve a su lugar al reponer: no hace falta crear ni destruir nada.
     */
    this.productMeshes = [];
    for (const c of this.columns) {
      const im = new THREE.InstancedMesh(this.geoms[c.productId], mat, c.slots.length);
      im.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      // los productos no proyectan sombra (ahorra la mitad del costo); el piso ya trae AO horneada
      im.castShadow = false;
      im.receiveShadow = true;
      im.frustumCulled = false;
      im.userData.dirty = false;
      c.slots.forEach((s, i) => {
        s.mesh = im;
        s.idx = i;
        im.setMatrixAt(i, this.slotMatrix(s, 0, 0, 1, _m));
      });
      this.productMeshes.push(im);
      this.scene.add(im);
    }
  }

  /** Matriz de una unidad en el estante, con un pequeño meneo opcional. */
  slotMatrix(s, wig, hop, scale, out) {
    _e.set(s.rotX + wig * 0.35, s.rotY + wig, wig * 0.5);
    _q.setFromEuler(_e);
    _v.copy(s.pos);
    _v.y += hop;
    _s.set(scale, scale, scale);
    return out.compose(_v, _q, _s);
  }

  setSlot(s, m) {
    s.mesh.setMatrixAt(s.idx, m);
    s.mesh.userData.dirty = true;
  }

  hideSlot(s) {
    _m.makeScale(0, 0, 0);
    this.setSlot(s, _m);
  }

  /** La unidad vuelve a su lugar en el estante. */
  shelveSlot(s) {
    s.taken = false;
    this.setSlot(s, this.slotMatrix(s, 0, 0, 1, _m));
  }

  /** Sube a la GPU solo las mallas que cambiaron este cuadro. */
  flush() {
    for (const im of this.productMeshes) {
      if (im.userData.dirty) {
        im.instanceMatrix.needsUpdate = true;
        im.userData.dirty = false;
      }
    }
  }

  /** Vuelve a llenar los estantes (inicio de ronda). */
  restock() {
    for (const c of this.columns) for (const s of c.slots) this.shelveSlot(s);
  }

  /** Siguiente unidad disponible de una columna (la de más adelante/arriba). */
  nextSlot(col) {
    for (const s of col.slots) if (!s.taken) return s;
    return null;
  }

  freeSlot(col) {
    for (let i = col.slots.length - 1; i >= 0; i--) if (col.slots[i].taken) return col.slots[i];
    return null;
  }

  /* ------------------------------------------------------------ ayudas visuales */

  buildHelpers() {
    // contorno del producto señalado (casco invertido)
    this.outline = new THREE.Mesh(this.geoms[PRODUCTS[0].id], new THREE.MeshBasicMaterial({ color: 0xfff3a0, side: THREE.BackSide, toneMapped: false }));
    this.outline.visible = false;
    this.scene.add(this.outline);

    // sombras redondas bajo personajes y carritos
    this.blobTex = buildBlobTexture();
    this.blobs = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: this.blobTex, transparent: true, depthWrite: false, toneMapped: false }), 12);
    this.blobs.count = 0;
    this.blobs.renderOrder = 1;
    this.blobs.frustumCulled = false;
    this.scene.add(this.blobs);

    // aro + flecha sobre la caja
    const ringTex = buildRingTexture();
    this.beacon = new THREE.Group();
    const ring = new THREE.Mesh(new THREE.PlaneGeometry(2.4, 2.4).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: ringTex, color: 0x3ec6ff, transparent: true, depthWrite: false, toneMapped: false }));
    ring.position.y = 0.02;
    const arrow = new THREE.Mesh(
      merge([part(new THREE.ConeGeometry(0.26, 0.4, 4), 0x95e7ff, { rot: [Math.PI, Math.PI / 4, 0] }), part(cyl(0.09, 0.09, 0.35, 8), 0x95e7ff, { pos: [0, 0.35, 0] })]),
      new THREE.MeshStandardMaterial({ vertexColors: true, emissive: 0x2a8fbf, emissiveIntensity: 0.6, roughness: 0.4 }),
    );
    arrow.position.y = 2.1;
    this.beacon.add(ring, arrow);
    this.beacon.position.set(CHECKOUT.padX, 0, CHECKOUT.padZ);
    this.beacon.visible = false;
    this.beaconRing = ring;
    this.beaconArrow = arrow;
    this.scene.add(this.beacon);

    // brillo de pista sobre una columna
    this.hintRing = new THREE.Mesh(new THREE.PlaneGeometry(1.4, 1.4).rotateX(-Math.PI / 2), new THREE.MeshBasicMaterial({ map: ringTex, color: 0xffd23f, transparent: true, depthWrite: false, toneMapped: false }));
    this.hintRing.visible = false;
    this.scene.add(this.hintRing);
  }

  setBlobs(list) {
    // list: [{x,z,r}]
    const n = Math.min(list.length, 12);
    for (let i = 0; i < n; i++) {
      const b = list[i];
      _q.setFromAxisAngle(UP, b.rot || 0);
      _m.compose(_v.set(b.x, 0.012 + i * 0.001, b.z), _q, _s.set(b.sx, 1, b.sz));
      this.blobs.setMatrixAt(i, _m);
    }
    this.blobs.count = n;
    this.blobs.instanceMatrix.needsUpdate = true;
  }
}

export { cartGeometry, wheelGeometry };
