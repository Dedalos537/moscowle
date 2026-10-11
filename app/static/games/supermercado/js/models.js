/*
 * Modelado procedural: todo se arma con primitivas (cajas redondeadas, esferas, tornos, tubos)
 * fusionadas en una sola geometría con colores por vértice. Así cada producto, personaje o mueble
 * cuesta una sola llamada de dibujo.
 */
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/BufferGeometryUtils.js';
import { WHITE_UV } from './textures.js';

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _s = new THREE.Vector3();
const _p = new THREE.Vector3();
const _c = new THREE.Color();
const _c2 = new THREE.Color();
const _base = new THREE.Color();
const _cv = new THREE.Color();

export const P_SCALE = 1.35;

/**
 * Prepara una primitiva para fusionarse: la transforma, le pone color por vértice y reubica su uv
 * en el atlas (o en un píxel blanco si no lleva etiqueta).
 * o: { pos, rot, scale, uv, colorFn(x,y,z,color) }
 */
export function part(geo, color, o = {}) {
  let g = geo.index ? geo.toNonIndexed() : geo;
  for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
  if (!g.attributes.uv) g.setAttribute('uv', new THREE.Float32BufferAttribute(new Float32Array(g.attributes.position.count * 2), 2));
  if (!g.attributes.normal) g.computeVertexNormals();
  const r = o.rot || [0, 0, 0];
  _e.set(r[0], r[1], r[2], o.order || 'XYZ');
  _q.setFromEuler(_e);
  const pp = o.pos || [0, 0, 0];
  const sc = o.scale || [1, 1, 1];
  _m.compose(_p.set(pp[0], pp[1], pp[2]), _q, _s.set(sc[0], sc[1], sc[2]));
  g.applyMatrix4(_m);
  const pos = g.attributes.position;
  const n = pos.count;
  const col = new Float32Array(n * 3);
  _base.set(color);
  for (let i = 0; i < n; i++) {
    _cv.copy(_base);
    if (o.colorFn) o.colorFn(pos.getX(i), pos.getY(i), pos.getZ(i), _cv);
    col[i * 3] = _cv.r;
    col[i * 3 + 1] = _cv.g;
    col[i * 3 + 2] = _cv.b;
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const uv = g.attributes.uv;
  const rect = o.uv || WHITE_UV;
  for (let i = 0; i < n; i++) {
    if (o.uv) uv.setXY(i, rect.x + uv.getX(i) * rect.w, rect.y + uv.getY(i) * rect.h);
    else uv.setXY(i, rect.x, rect.y);
  }
  uv.needsUpdate = true;
  g.clearGroups();
  return g;
}

export function merge(parts) {
  const g = mergeGeometries(parts, false);
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}

/* primitivas cortas */
export const rbox = (w, h, d, r = 0.02, seg = 1) => new RoundedBoxGeometry(w, h, d, seg, Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001));
export const box = (w, h, d) => new THREE.BoxGeometry(w, h, d);
export const cyl = (rt, rb, h, seg = 12, open = false, ts = 0, tl = Math.PI * 2) => new THREE.CylinderGeometry(rt, rb, h, seg, 1, open, ts, tl);
export const sph = (r, ws = 10, hs = 8, ps = 0, pl = Math.PI * 2, ts = 0, tl = Math.PI) => new THREE.SphereGeometry(r, ws, hs, ps, pl, ts, tl);
export const quad = (w, h) => new THREE.PlaneGeometry(w, h);
const lathe = (pts, seg = 12) => new THREE.LatheGeometry(pts.map(([x, y]) => new THREE.Vector2(x, y)), seg, Math.PI, Math.PI * 2);

/** Mezcla de color en función de la altura (para degradados suaves en frutas y panes). */
function grad(top, y0, y1) {
  const t = new THREE.Color(top);
  return (x, y, z, c) => {
    const k = THREE.MathUtils.clamp((y - y0) / (y1 - y0), 0, 1);
    c.lerp(t, k * k);
  };
}

/** Banda de etiqueta cilíndrica: el centro del texto queda mirando al frente (+z). */
function labelBand(r, h, y, uv, seg = 14) {
  return part(cyl(r, r, h, seg, true, Math.PI, Math.PI * 2), 0xffffff, { pos: [0, y, 0], uv });
}

function bottle(profile, tint, capColor, uv, bandY, bandH, bandR) {
  const parts = [
    part(lathe(profile, 12), tint, {
      colorFn: (x, y, z, c) => {
        // brillo vertical del plástico
        const k = 0.5 + 0.5 * Math.sin(Math.atan2(x, z) * 1 + 0.8);
        c.lerp(_c2.set(0xffffff), 0.18 * k);
      },
    }),
  ];
  const top = profile[profile.length - 1][1];
  const capR = profile[profile.length - 2][0] + 0.004;
  parts.push(part(cyl(capR, capR, 0.03, 10), capColor, { pos: [0, top + 0.012, 0] }));
  if (uv) parts.push(labelBand(bandR, bandH, bandY, uv));
  return parts;
}

function labelFront(w, h, y, z, uv, x = 0) {
  return part(quad(w, h), 0xffffff, { pos: [x, y, z], uv });
}

/* ------------------------------------------------------------------ productos */

const BUILDERS = {
  apple: () => [
    part(sph(0.1, 12, 9), 0xc8302a, { pos: [0, 0.092, 0], scale: [1, 0.92, 1], colorFn: grad(0xff7a55, 0.02, 0.2) }),
    part(cyl(0.008, 0.011, 0.06, 6), 0x6b3f1d, { pos: [0, 0.2, 0], rot: [0, 0, 0.2] }),
    part(sph(0.04, 8, 6), 0x5aa83a, { pos: [0.035, 0.205, 0], scale: [1, 0.25, 0.55], rot: [0, 0, 0.45] }),
  ],
  banana: () => {
    const parts = [];
    for (let i = 0; i < 3; i++) {
      const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(-0.14, 0.13, 0), new THREE.Vector3(0, -0.04, 0), new THREE.Vector3(0.14, 0.13, 0));
      const g = new THREE.TubeGeometry(curve, 10, 0.034, 6, false);
      parts.push(
        part(g, 0xffd84a, {
          pos: [0, 0.035 + i * 0.012, (i - 1) * 0.055],
          rot: [0.25 * (i - 1), 0.12 * (i - 1), 0],
          colorFn: (x, y, z, c) => c.lerp(_c.set(0x9fcf4a), Math.min(1, Math.max(0, Math.abs(x) - 0.08) * 14)),
        }),
      );
    }
    parts.push(part(sph(0.03, 8, 6), 0x5b3415, { pos: [-0.145, 0.16, 0] }));
    return parts;
  },
  mango: () => [
    part(sph(0.1, 12, 9), 0xffb22e, {
      pos: [0, 0.085, 0],
      scale: [1.25, 0.85, 0.9],
      colorFn: (x, y, z, c) => c.lerp(_c.set(0xe8452f), THREE.MathUtils.clamp((y - 0.08) * 6 + x * 3, 0, 0.85)),
    }),
    part(cyl(0.007, 0.01, 0.035, 6), 0x5b3415, { pos: [-0.1, 0.15, 0], rot: [0, 0, 0.6] }),
  ],
  lime: () => [
    part(sph(0.07, 10, 8), 0x5fb83a, { pos: [0, 0.066, 0], scale: [1.12, 0.95, 1], colorFn: grad(0x9be05a, 0, 0.13) }),
    part(sph(0.012, 6, 5), 0x4e8a2a, { pos: [0.078, 0.07, 0] }),
  ],
  avocado: () => [
    part(
      lathe([[0, 0], [0.06, 0.006], [0.085, 0.04], [0.08, 0.09], [0.058, 0.14], [0.038, 0.18], [0.02, 0.198], [0, 0.2]], 16),
      0x2f5a22,
      { colorFn: grad(0x4f7d2c, 0, 0.2) },
    ),
    part(cyl(0.006, 0.008, 0.025, 6), 0x5b3415, { pos: [0, 0.205, 0] }),
  ],
  corn: () => [
    part(new THREE.CapsuleGeometry(0.05, 0.18, 3, 10), 0xf5d04a, {
      pos: [0, 0.06, 0],
      rot: [0, 0, Math.PI / 2],
      colorFn: (x, y, z, c) => {
        const k = Math.sin(x * 160) * Math.sin(Math.atan2(y - 0.06, z) * 9);
        c.lerp(_c.set(k > 0 ? 0xffe680 : 0xe0b02a), 0.55);
      },
    }),
    part(sph(0.06, 10, 8), 0x7cc36b, { pos: [-0.13, 0.065, 0.025], scale: [1.8, 0.55, 0.6], rot: [0.5, 0, 0.1] }),
    part(sph(0.06, 10, 8), 0x5aa83a, { pos: [-0.13, 0.06, -0.03], scale: [1.7, 0.5, 0.6], rot: [-0.6, 0, -0.1] }),
  ],
  bun: () => [
    part(sph(0.09, 12, 8), 0xe0a050, { pos: [0, 0.055, 0], scale: [1.25, 0.66, 0.95], colorFn: grad(0xb8682a, 0.03, 0.12) }),
    part(sph(0.03, 8, 6), 0xf3cf8e, { pos: [0, 0.112, 0], scale: [2.6, 0.3, 0.5] }),
  ],
  panettone: (uv) => [
    part(cyl(0.11, 0.11, 0.17, 14), 0x2f6fd6, { pos: [0, 0.085, 0] }),
    labelBand(0.112, 0.12, 0.085, uv, 14),
    part(sph(0.112, 14, 5, 0, Math.PI * 2, 0, Math.PI / 2), 0xb5651d, { pos: [0, 0.165, 0], scale: [1, 0.55, 1], colorFn: grad(0x7a3e12, 0.17, 0.23) }),
    part(sph(0.012, 6, 4), 0x3a1a0a, { pos: [0.04, 0.215, 0.04] }),
    part(sph(0.012, 6, 4), 0x3a1a0a, { pos: [-0.05, 0.205, 0.02] }),
    part(sph(0.012, 6, 4), 0xc81d3a, { pos: [0.0, 0.222, -0.03] }),
  ],
  cookies: (uv, p) => [
    part(rbox(0.2, 0.25, 0.07, 0.018), p.label[1], { pos: [0, 0.125, 0] }),
    labelFront(0.18, 0.11, 0.17, 0.0355, uv),
    part(cyl(0.04, 0.04, 0.012, 16), p.id === 'galletas_choco' ? 0x5a2e14 : 0xf3cf8e, { pos: [-0.04, 0.06, 0.04], rot: [Math.PI / 2, 0, 0] }),
    part(cyl(0.04, 0.04, 0.012, 16), p.id === 'galletas_choco' ? 0x7a3e1d : 0xffe1a8, { pos: [0.03, 0.055, 0.042], rot: [Math.PI / 2, 0, 0.3] }),
  ],
  cake: () => [
    part(rbox(0.26, 0.11, 0.13, 0.035), 0xc98a46, { pos: [0, 0.055, 0], colorFn: grad(0x8a4a1c, 0.05, 0.11) }),
    part(rbox(0.27, 0.03, 0.14, 0.014), 0xfff6e8, { pos: [0, 0.112, 0] }),
    part(sph(0.016, 8, 6), 0xfff6e8, { pos: [-0.07, 0.092, 0.068], scale: [1, 1.6, 0.7] }),
    part(sph(0.016, 8, 6), 0xfff6e8, { pos: [0.04, 0.088, 0.068], scale: [1, 2, 0.7] }),
    part(sph(0.018, 8, 6), 0xe63946, { pos: [0, 0.135, 0] }),
  ],
  carton: (uv, p) => [
    part(rbox(0.13, 0.2, 0.13, 0.012), p.tint ?? 0xffffff, { pos: [0, 0.1, 0] }),
    part(cyl(0.075, 0.075, 0.128, 3), p.label[1], { pos: [0, 0.219, 0], rot: [-Math.PI / 2, 0, 0], scale: [1, 1, 0.5] }),
    labelFront(0.122, 0.12, 0.095, 0.0662, uv),
    part(cyl(0.018, 0.018, 0.022, 10), 0xffffff, { pos: [0.03, 0.235, 0.03] }),
  ],
  yogurt: (uv, p) =>
    bottle([[0, 0], [0.045, 0], [0.05, 0.012], [0.05, 0.11], [0.04, 0.145], [0.026, 0.165], [0.026, 0.18]], 0xffe6f0, p.label[1], uv, 0.065, 0.075, 0.0512),
  cheese: () => {
    const r = 0.12;
    const h = 0.09;
    const cut = 0.65;
    const holes = (x, y, z, c) => {
      const k = Math.sin(x * 70 + z * 30) * Math.sin(y * 90 + z * 50);
      if (k > 0.72) c.lerp(_c.set(0xd99a1a), 0.6);
    };
    return [
      part(cyl(r, r, h, 16, false, cut, Math.PI * 2 - cut * 2), 0xf7c843, { pos: [0, h / 2, 0], colorFn: holes }),
      part(quad(r, h), 0xffde6b, { pos: [(r / 2) * Math.sin(cut), h / 2, (r / 2) * Math.cos(cut)], rot: [0, cut - Math.PI / 2, 0], colorFn: holes }),
      part(quad(r, h), 0xffde6b, { pos: [(r / 2) * Math.sin(-cut), h / 2, (r / 2) * Math.cos(-cut)], rot: [0, -cut + Math.PI / 2, 0], colorFn: holes }),
      part(cyl(r + 0.004, r + 0.004, 0.022, 16, true, cut, Math.PI * 2 - cut * 2), 0xd94a3a, { pos: [0, 0.012, 0] }),
    ];
  },
  eggs: () => {
    const parts = [part(rbox(0.25, 0.06, 0.15, 0.018), 0xcdb894, { pos: [0, 0.03, 0] })];
    for (let i = 0; i < 3; i++)
      for (let j = 0; j < 2; j++)
        parts.push(part(sph(0.034, 8, 6), j ? 0xfff3df : 0xf2d2a8, { pos: [(i - 1) * 0.075, 0.07, (j - 0.5) * 0.068], scale: [1, 1.2, 1], colorFn: grad(0xffffff, 0.04, 0.11) }));
    return parts;
  },
  butter: (uv, p) => [part(rbox(0.16, 0.07, 0.1, 0.014), p.label[1], { pos: [0, 0.035, 0] }), labelFront(0.15, 0.05, 0.036, 0.0505, uv)],
  bottle_big: (uv, p) =>
    bottle([[0, 0], [0.06, 0], [0.068, 0.012], [0.068, 0.2], [0.062, 0.245], [0.034, 0.29], [0.022, 0.302], [0.022, 0.32]], p.tint, p.label[1], uv, 0.13, 0.085, 0.0695),
  bottle_small: (uv, p) =>
    bottle([[0, 0], [0.045, 0], [0.05, 0.01], [0.05, 0.14], [0.044, 0.17], [0.024, 0.2], [0.017, 0.21], [0.017, 0.225]], p.tint, p.label[1], uv, 0.09, 0.065, 0.0512),
  soda: (uv, p) =>
    bottle([[0, 0], [0.055, 0], [0.062, 0.02], [0.056, 0.06], [0.062, 0.12], [0.06, 0.19], [0.032, 0.26], [0.02, 0.28], [0.02, 0.3]], p.tint, 0xe63946, uv, 0.15, 0.07, 0.0612),
  sack: (uv, p) => [
    part(rbox(0.21, 0.25, 0.11, 0.045, 2), 0xfffaf0, { pos: [0, 0.125, 0], colorFn: grad(0xe8e0d0, 0.2, 0.0) }),
    part(rbox(0.21, 0.03, 0.05, 0.01), 0xf0e6d6, { pos: [0, 0.255, 0] }),
    labelFront(0.17, 0.12, 0.115, 0.0565, uv),
  ],
  pasta: (uv) => [
    part(rbox(0.1, 0.3, 0.06, 0.016), 0xf3d98b, { pos: [0, 0.15, 0], colorFn: (x, y, z, c) => c.lerp(_c.set(0xffe9a8), Math.abs(Math.sin(x * 120)) * 0.6) }),
    labelFront(0.096, 0.11, 0.17, 0.0308, uv),
  ],
  oil: (uv, p) =>
    bottle([[0, 0], [0.055, 0], [0.062, 0.012], [0.062, 0.21], [0.05, 0.26], [0.024, 0.3], [0.02, 0.315], [0.02, 0.33]], p.tint, 0xe63946, uv, 0.12, 0.1, 0.0632),
  can: (uv) => [
    part(cyl(0.07, 0.07, 0.065, 14), 0xc9ccd4, { pos: [0, 0.0325, 0] }),
    labelBand(0.0712, 0.046, 0.0325, uv),
    part(cyl(0.062, 0.062, 0.004, 14), 0xe9ecf2, { pos: [0, 0.066, 0] }),
  ],
  cereal_big: (uv, p) => [part(rbox(0.21, 0.33, 0.075, 0.014), p.label[1], { pos: [0, 0.165, 0] }), labelFront(0.19, 0.12, 0.23, 0.0378, uv), part(sph(0.05, 12, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), 0xffffff, { pos: [0, 0.11, 0.0378], scale: [1, 0.8, 0.12] }), part(sph(0.02, 8, 6), 0xffb22e, { pos: [-0.015, 0.115, 0.04], scale: [1, 1, 0.3] }), part(sph(0.02, 8, 6), 0xe85d3a, { pos: [0.018, 0.112, 0.04], scale: [1, 1, 0.3] })],
  cereal_small: (uv, p) => [part(rbox(0.16, 0.25, 0.06, 0.012), p.label[1], { pos: [0, 0.125, 0] }), labelFront(0.15, 0.1, 0.17, 0.0302, uv), part(sph(0.04, 12, 8, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), 0xffffff, { pos: [0, 0.08, 0.0302], scale: [1, 0.8, 0.12] })],
  soap: (uv, p) => [part(rbox(0.15, 0.07, 0.09, 0.02), p.label[1], { pos: [0, 0.035, 0] }), labelFront(0.13, 0.045, 0.036, 0.0455, uv)],
  jug: (uv, p) => [
    part(rbox(0.16, 0.27, 0.11, 0.045, 2), p.label[1], { pos: [0, 0.135, 0], colorFn: grad(0x8fd0ff, 0.0, 0.4) }),
    part(new THREE.TorusGeometry(0.05, 0.016, 6, 12, Math.PI), p.label[1], { pos: [0.02, 0.26, 0], rot: [0, 0, 0] }),
    part(cyl(0.024, 0.024, 0.04, 12), 0xffffff, { pos: [-0.05, 0.285, 0] }),
    labelFront(0.13, 0.11, 0.12, 0.0555, uv),
  ],
  rolls: (uv) => {
    const parts = [];
    for (let i = 0; i < 2; i++)
      for (let j = 0; j < 2; j++) {
        parts.push(part(cyl(0.056, 0.056, 0.13, 10), 0xffffff, { pos: [(i - 0.5) * 0.114, 0.065, (j - 0.5) * 0.114], colorFn: grad(0xf2f2f2, 0.13, 0) }));
        parts.push(part(cyl(0.018, 0.018, 0.002, 10), 0xc8a978, { pos: [(i - 0.5) * 0.114, 0.131, (j - 0.5) * 0.114] }));
      }
    parts.push(labelFront(0.2, 0.07, 0.065, 0.1145, uv));
    return parts;
  },
  sponge: () => [
    part(rbox(0.14, 0.055, 0.095, 0.014), 0xffd84a, { pos: [0, 0.0275, 0], colorFn: (x, y, z, c) => (Math.sin(x * 140) * Math.sin(z * 140) > 0.6 ? c.lerp(_c.set(0xe8b820), 0.6) : c) }),
    part(rbox(0.14, 0.022, 0.095, 0.008), 0x3aa65a, { pos: [0, 0.066, 0] }),
  ],
  jar: (uv, p) => [
    part(lathe([[0, 0], [0.058, 0], [0.064, 0.012], [0.064, 0.13], [0.054, 0.15], [0, 0.15]], 12), p.tint),
    part(cyl(0.058, 0.058, 0.034, 12), 0xd4a537, { pos: [0, 0.16, 0] }),
    labelBand(0.0655, 0.07, 0.07, uv),
  ],
  jam: (uv, p) => [
    part(lathe([[0, 0], [0.055, 0], [0.06, 0.01], [0.06, 0.11], [0.05, 0.125], [0, 0.125]], 12), p.tint),
    part(cyl(0.058, 0.058, 0.03, 12), 0xffffff, {
      pos: [0, 0.138, 0],
      colorFn: (x, y, z, c) => (((Math.floor(x * 60) + Math.floor(z * 60)) & 1) === 0 ? c.set(0xd62839) : c),
    }),
    labelBand(0.0612, 0.05, 0.06, uv),
  ],
  oats: (uv) => [part(cyl(0.068, 0.068, 0.23, 14), 0xc08a4b, { pos: [0, 0.115, 0] }), labelBand(0.0695, 0.15, 0.11, uv), part(cyl(0.07, 0.07, 0.02, 14), 0xe63946, { pos: [0, 0.235, 0] })],
  bar: (uv, p) => [
    part(rbox(0.1, 0.18, 0.026, 0.008), p.label[1], { pos: [0, 0.09, 0] }),
    part(rbox(0.1, 0.035, 0.028, 0.008), 0xd8dce4, { pos: [0, 0.168, 0] }),
    labelFront(0.09, 0.08, 0.085, 0.0135, uv),
  ],
  chips: (uv, p) => [
    part(rbox(0.18, 0.22, 0.075, 0.034, 2), p.label[1], { pos: [0, 0.115, 0] }),
    part(box(0.18, 0.022, 0.02), 0xfff27a, { pos: [0, 0.226, 0] }),
    part(box(0.18, 0.018, 0.02), 0xfff27a, { pos: [0, 0.006, 0] }),
    labelFront(0.15, 0.09, 0.12, 0.0385, uv),
  ],
};

/** Geometría (escala de juguete) de un producto. */
export function productGeometry(p, uvs) {
  const parts = BUILDERS[p.shape](uvs[p.id], p);
  const g = merge(parts);
  g.scale(P_SCALE, P_SCALE, P_SCALE);
  g.computeBoundingBox();
  g.computeBoundingSphere();
  return g;
}

/* ------------------------------------------------------------------ personajes */

/**
 * Personaje "de juguete": cabeza grande, cuerpo corto. Devuelve geometrías por pieza para animarlas.
 * Pivotes: brazos en el hombro, piernas en la cadera, cabeza en el cuello.
 */
export function characterGeometries(o) {
  const skin = o.skin;
  const head = [
    part(sph(0.25, 20, 14), skin, { pos: [0, 0.23, 0], colorFn: grad(0xffffff, 0.15, 0.6) }),
    // pelo
    part(sph(0.262, 22, 12, 0, Math.PI * 2, 0, Math.PI * 0.52), o.hair, { pos: [0, 0.245, -0.012], rot: [-0.32, 0, 0] }),
    part(sph(0.12, 12, 8), o.hair, { pos: [0.1, 0.38, 0.13], scale: [1.2, 0.5, 0.8], rot: [0.4, 0, -0.3] }),
    part(sph(0.1, 12, 8), o.hair, { pos: [-0.1, 0.39, 0.14], scale: [1.2, 0.5, 0.8], rot: [0.5, 0, 0.4] }),
    // orejas
    part(sph(0.05, 8, 6), skin, { pos: [0.245, 0.22, 0], scale: [0.6, 1, 1] }),
    part(sph(0.05, 8, 6), skin, { pos: [-0.245, 0.22, 0], scale: [0.6, 1, 1] }),
    // mejillas y nariz
    part(sph(0.045, 10, 6), 0xff8f8f, { pos: [0.135, 0.17, 0.2], scale: [1, 0.6, 0.4] }),
    part(sph(0.045, 10, 6), 0xff8f8f, { pos: [-0.135, 0.17, 0.2], scale: [1, 0.6, 0.4] }),
    part(sph(0.03, 8, 6), skin, { pos: [0, 0.2, 0.245], colorFn: (x, y, z, c) => c.multiplyScalar(0.92) }),
    // boca
    part(new THREE.TorusGeometry(0.035, 0.009, 5, 10, Math.PI), 0x7a2e1d, { pos: [0, 0.145, 0.232], rot: [0.15, 0, Math.PI] }),
  ];
  if (o.cap) {
    head.push(part(sph(0.268, 20, 10, 0, Math.PI * 2, 0, Math.PI * 0.42), o.cap, { pos: [0, 0.25, 0], rot: [-0.18, 0, 0] }));
    head.push(part(cyl(0.16, 0.17, 0.02, 18, false, -Math.PI / 2, Math.PI), o.cap, { pos: [0, 0.37, 0.12], rot: [0.28, 0, 0], scale: [1, 1, 1.25] }));
  }
  if (o.bun) head.push(part(sph(0.1, 12, 8), o.hair, { pos: [0, 0.5, -0.1] }));
  if (o.glasses) {
    head.push(part(new THREE.TorusGeometry(0.055, 0.01, 6, 16), 0x3a2a20, { pos: [0.085, 0.24, 0.225] }));
    head.push(part(new THREE.TorusGeometry(0.055, 0.01, 6, 16), 0x3a2a20, { pos: [-0.085, 0.24, 0.225] }));
  }
  const eyes = [
    part(sph(0.036, 10, 8), 0x2a1a12, { pos: [0.085, 0.245, 0.218], scale: [0.85, 1.15, 0.6] }),
    part(sph(0.036, 10, 8), 0x2a1a12, { pos: [-0.085, 0.245, 0.218], scale: [0.85, 1.15, 0.6] }),
    part(sph(0.012, 6, 4), 0xffffff, { pos: [0.095, 0.26, 0.24] }),
    part(sph(0.012, 6, 4), 0xffffff, { pos: [-0.075, 0.26, 0.24] }),
  ];
  const torso = [
    part(rbox(0.36, 0.34, 0.26, 0.11, 2), o.shirt, { pos: [0, 0.17, 0], colorFn: grad(0xffffff, 0.25, 0.4) }),
    part(cyl(0.07, 0.08, 0.06, 10), skin, { pos: [0, 0.35, 0] }),
  ];
  if (o.apron) {
    torso.push(part(rbox(0.3, 0.3, 0.04, 0.03), o.apron, { pos: [0, 0.15, 0.125] }));
    torso.push(part(rbox(0.08, 0.05, 0.01, 0.01), 0xffffff, { pos: [0.08, 0.24, 0.15] }));
  }
  if (o.backpack) {
    torso.push(part(rbox(0.26, 0.28, 0.12, 0.06), o.backpack, { pos: [0, 0.19, -0.17] }));
    torso.push(part(rbox(0.18, 0.1, 0.05, 0.03), 0xffffff, { pos: [0, 0.12, -0.24], colorFn: (x, y, z, c) => c.lerp(_c.set(o.backpack), 0.4) }));
  }
  const arm = (side) => [
    part(sph(0.075, 10, 8), o.shirt, { pos: [0, -0.02, 0] }),
    part(new THREE.CapsuleGeometry(0.052, 0.17, 4, 8), skin, { pos: [0, -0.15, 0] }),
    part(sph(0.06, 10, 8), skin, { pos: [0, -0.27, 0.0] }),
  ];
  const leg = () => [
    part(new THREE.CapsuleGeometry(0.07, 0.1, 4, 10), o.pants, { pos: [0, -0.08, 0] }),
    part(new THREE.CapsuleGeometry(0.055, 0.08, 4, 8), skin, { pos: [0, -0.2, 0] }),
    part(rbox(0.13, 0.08, 0.2, 0.035), o.shoes, { pos: [0, -0.3, 0.035] }),
    part(rbox(0.135, 0.02, 0.205, 0.008), 0xffffff, { pos: [0, -0.335, 0.035] }),
  ];
  return {
    head: merge(head),
    eyes: merge(eyes),
    torso: merge(torso),
    armL: merge(arm(1)),
    armR: merge(arm(-1)),
    legL: merge(leg()),
    legR: merge(leg()),
  };
}

/* ------------------------------------------------------------------ carrito */

/** Carrito de juguete; el frente mira a +z. Las ruedas van aparte (giran). */
export function cartGeometry(color = 0xc58cff, trim = 0xffd28f) {
  const W = 0.66;
  const D = 0.5;
  const yb = 0.26;
  const H = 0.3;
  const t = 0.035;
  const c = new THREE.Color(color);
  const darker = c.clone().multiplyScalar(0.8).getHex();
  const holes = (x, y, z, col) => {
    // rejilla del canasto
    const gx = Math.abs(Math.sin(x * 34)) > 0.86 || Math.abs(Math.sin(z * 34)) > 0.86;
    const gy = Math.abs(Math.sin(y * 34)) > 0.86;
    if (gx || gy) col.multiplyScalar(0.82);
  };
  const metal = 0x9aa0ad;
  const parts = [
    part(rbox(W, t, D, 0.015), darker, { pos: [0, yb, 0] }),
    part(rbox(W, H, t, 0.015), color, { pos: [0, yb + H / 2, D / 2], colorFn: holes }),
    part(rbox(W, H * 0.9, t, 0.015), color, { pos: [0, yb + H * 0.45, -D / 2], colorFn: holes }),
    part(rbox(t, H, D, 0.015), color, { pos: [W / 2, yb + H / 2, 0], colorFn: holes }),
    part(rbox(t, H, D, 0.015), color, { pos: [-W / 2, yb + H / 2, 0], colorFn: holes }),
    // borde superior
    part(rbox(W + 0.05, 0.035, 0.05, 0.016), trim, { pos: [0, yb + H, D / 2] }),
    part(rbox(W + 0.05, 0.035, 0.05, 0.016), trim, { pos: [0, yb + H * 0.9, -D / 2] }),
    part(rbox(0.05, 0.035, D + 0.05, 0.016), trim, { pos: [W / 2, yb + H, 0] }),
    part(rbox(0.05, 0.035, D + 0.05, 0.016), trim, { pos: [-W / 2, yb + H, 0] }),
    // chasis
    part(cyl(0.018, 0.018, yb, 8), metal, { pos: [W / 2 - 0.05, yb / 2, D / 2 - 0.05] }),
    part(cyl(0.018, 0.018, yb, 8), metal, { pos: [-W / 2 + 0.05, yb / 2, D / 2 - 0.05] }),
    part(cyl(0.018, 0.018, yb, 8), metal, { pos: [W / 2 - 0.05, yb / 2, -D / 2 + 0.05] }),
    part(cyl(0.018, 0.018, yb, 8), metal, { pos: [-W / 2 + 0.05, yb / 2, -D / 2 + 0.05] }),
    part(rbox(W - 0.06, 0.03, D - 0.04, 0.012), 0xb7bcc7, { pos: [0, 0.07, 0] }),
    // manubrio (a la altura de las manos del niño)
    part(rbox(0.03, 0.03, 0.14, 0.01), metal, { pos: [W / 2 - 0.04, yb + H * 0.9 + 0.01, -D / 2 - 0.06], rot: [-0.25, 0, 0] }),
    part(rbox(0.03, 0.03, 0.14, 0.01), metal, { pos: [-W / 2 + 0.04, yb + H * 0.9 + 0.01, -D / 2 - 0.06], rot: [-0.25, 0, 0] }),
    part(cyl(0.032, 0.032, W - 0.02, 12), 0xe63946, { pos: [0, yb + H * 0.9 + 0.03, -D / 2 - 0.13], rot: [0, 0, Math.PI / 2] }),
    // banderita
    part(cyl(0.008, 0.008, 0.36, 6), metal, { pos: [W / 2 - 0.02, yb + H + 0.18, D / 2 - 0.02] }),
    part(new THREE.ConeGeometry(0.06, 0.13, 3), trim, { pos: [W / 2 + 0.04, yb + H + 0.3, D / 2 - 0.02], rot: [0, 0, -Math.PI / 2], scale: [1, 1, 0.3] }),
  ];
  return merge(parts);
}

export function wheelGeometry() {
  return merge([
    part(cyl(0.06, 0.06, 0.045, 14), 0x3a3340, { rot: [0, 0, Math.PI / 2] }),
    part(cyl(0.028, 0.028, 0.05, 10), 0xfff3dc, { rot: [0, 0, Math.PI / 2] }),
  ]);
}

/** Bolsa de papel de la caja. */
export function bagGeometry() {
  return merge([
    part(rbox(0.36, 0.34, 0.24, 0.02), 0xd9a066, { pos: [0, 0.17, 0], colorFn: grad(0xe8b980, 0.0, 0.34) }),
    part(rbox(0.36, 0.04, 0.245, 0.01), 0xc48748, { pos: [0, 0.33, 0] }),
    part(new THREE.TorusGeometry(0.07, 0.012, 6, 12, Math.PI), 0xc48748, { pos: [0, 0.34, 0] }),
  ]);
}
