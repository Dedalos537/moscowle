/*
 * Texturas pintadas en canvas (sin imágenes externas): etiquetas de productos, letreros, precios,
 * piso con oclusión ambiental "horneada", cinta de la caja y pantalla de la registradora.
 */
import * as THREE from 'three';
import { PRODUCTS, SECTIONS, STORE, CHECKOUT, soles, PRODUCT_BY_ID } from './config.js';

export const FONT = '"SF Pro Rounded", ui-rounded, "Arial Rounded MT Bold", "Nunito", "Varela Round", "Trebuchet MS", system-ui, sans-serif';

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return c;
}

function rr(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function fitText(ctx, text, maxW, size, weight = 900) {
  let s = size;
  ctx.font = `${weight} ${s}px ${FONT}`;
  while (ctx.measureText(text).width > maxW && s > 10) {
    s -= 2;
    ctx.font = `${weight} ${s}px ${FONT}`;
  }
  return s;
}

function texFrom(c, { repeat = false, aniso = 4 } = {}) {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = aniso;
  if (repeat) t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

/* ---------------------------------------------------------------- etiquetas de productos */

const PA_W = 1024;
const PA_H = 1024;
const CELL_W = 256;
const CELL_H = 128;

/** uv del atlas de productos: { x, y, w, h } (origen abajo-izquierda, como en three). */
function cellUV(col, row, W, H, cw, ch, inset = 3) {
  const px = col * cw + inset;
  const py = row * ch + inset;
  const w = cw - inset * 2;
  const h = ch - inset * 2;
  return { x: px / W, y: 1 - (py + h) / H, w: w / W, h: h / H };
}

export const WHITE_UV = { x: (PA_W - 40) / PA_W, y: 8 / PA_H, w: 1 / PA_W, h: 1 / PA_H };

function drawLabel(ctx, x, y, w, h, [text, bg, ink], seed) {
  ctx.save();
  ctx.fillStyle = bg;
  ctx.fillRect(x, y, w, h);
  // motivo decorativo distinto por producto
  ctx.globalAlpha = 0.18;
  ctx.fillStyle = ink;
  const m = seed % 3;
  if (m === 0) {
    for (let i = 0; i < 8; i++) {
      ctx.beginPath();
      ctx.arc(x + ((i * 53) % w), y + ((i * 37) % h), 10 + (i % 3) * 6, 0, Math.PI * 2);
      ctx.fill();
    }
  } else if (m === 1) {
    for (let i = -2; i < 10; i++) ctx.fillRect(x + i * 34, y, 14, h);
  } else {
    ctx.beginPath();
    ctx.moveTo(x, y + h * 0.7);
    for (let i = 0; i <= 8; i++) ctx.quadraticCurveTo(x + i * 32 + 16, y + h * (i % 2 ? 0.55 : 0.85), x + i * 32 + 32, y + h * 0.7);
    ctx.lineTo(x + w, y + h);
    ctx.lineTo(x, y + h);
    ctx.fill();
  }
  ctx.globalAlpha = 1;
  // placa central
  ctx.fillStyle = 'rgba(255,255,255,0.22)';
  rr(ctx, x + 16, y + 26, w - 32, h - 52, 22);
  ctx.fill();
  const s = fitText(ctx, text, w - 48, 54);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.lineWidth = Math.max(4, s * 0.14);
  ctx.strokeStyle = 'rgba(0,0,0,0.18)';
  ctx.strokeText(text, x + w / 2, y + h / 2 + 3);
  ctx.fillStyle = ink;
  ctx.fillText(text, x + w / 2, y + h / 2 + 2);
  ctx.restore();
}

export function buildProductAtlas() {
  const c = canvas(PA_W, PA_H);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, PA_W, PA_H);
  const uvs = {};
  let i = 0;
  PRODUCTS.forEach((p, k) => {
    if (!p.label) return;
    const col = i % 4;
    const row = Math.floor(i / 4);
    drawLabel(ctx, col * CELL_W, row * CELL_H, CELL_W, CELL_H, p.label, k);
    uvs[p.id] = cellUV(col, row, PA_W, PA_H, CELL_W, CELL_H);
    i++;
  });
  // celda blanca garantizada para las partes sin etiqueta
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(PA_W - 64, PA_H - 64, 64, 64);
  const tex = texFrom(c, { aniso: 4 });
  return { tex, uvs };
}

/* ---------------------------------------------------------------- letreros y precios */

const SA_W = 2048;
const SA_H = 1024;

function drawSectionIcon(ctx, id, cx, cy, r) {
  ctx.save();
  ctx.translate(cx, cy);
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  const blob = (x, y, rx, ry, col) => {
    ctx.fillStyle = col;
    ctx.beginPath();
    ctx.ellipse(x, y, rx, ry, 0, 0, Math.PI * 2);
    ctx.fill();
  };
  if (id === 'frutas') {
    blob(-r * 0.25, r * 0.1, r * 0.55, r * 0.5, '#e24a3b');
    blob(r * 0.35, r * 0.15, r * 0.45, r * 0.42, '#ffb22e');
    ctx.fillStyle = '#4f9a3a';
    ctx.beginPath();
    ctx.ellipse(-r * 0.1, -r * 0.5, r * 0.25, r * 0.12, -0.6, 0, Math.PI * 2);
    ctx.fill();
  } else if (id === 'panaderia') {
    blob(0, r * 0.05, r * 0.85, r * 0.5, '#d98b3a');
    ctx.strokeStyle = '#a65a1c';
    ctx.lineWidth = r * 0.1;
    for (let i = -1; i <= 1; i++) {
      ctx.beginPath();
      ctx.moveTo(i * r * 0.35 - r * 0.12, -r * 0.2);
      ctx.lineTo(i * r * 0.35 + r * 0.12, r * 0.3);
      ctx.stroke();
    }
  } else if (id === 'lacteos') {
    ctx.fillStyle = '#ffffff';
    rr(ctx, -r * 0.45, -r * 0.4, r * 0.9, r * 1.15, r * 0.12);
    ctx.fill();
    ctx.fillStyle = '#3c7be0';
    ctx.beginPath();
    ctx.moveTo(-r * 0.45, -r * 0.4);
    ctx.lineTo(0, -r * 0.85);
    ctx.lineTo(r * 0.45, -r * 0.4);
    ctx.fill();
    blob(0, r * 0.2, r * 0.22, r * 0.2, '#3c7be0');
  } else if (id === 'bebidas') {
    ctx.fillStyle = '#4fb7ff';
    rr(ctx, -r * 0.3, -r * 0.45, r * 0.6, r * 1.25, r * 0.22);
    ctx.fill();
    ctx.fillStyle = '#1d4f8a';
    rr(ctx, -r * 0.14, -r * 0.85, r * 0.28, r * 0.3, r * 0.06);
    ctx.fill();
    ctx.fillStyle = '#ffffff';
    rr(ctx, -r * 0.3, 0, r * 0.6, r * 0.32, 4);
    ctx.fill();
  } else if (id === 'abarrotes') {
    ctx.fillStyle = '#fff6e0';
    rr(ctx, -r * 0.6, -r * 0.6, r * 1.2, r * 1.3, r * 0.3);
    ctx.fill();
    ctx.fillStyle = '#3aa65a';
    rr(ctx, -r * 0.6, -r * 0.05, r * 1.2, r * 0.4, 6);
    ctx.fill();
  } else if (id === 'limpieza') {
    blob(-r * 0.4, -r * 0.35, r * 0.22, r * 0.22, 'rgba(255,255,255,0.9)');
    blob(r * 0.45, -r * 0.55, r * 0.15, r * 0.15, 'rgba(255,255,255,0.9)');
    ctx.fillStyle = '#ff9ecf';
    rr(ctx, -r * 0.55, -r * 0.1, r * 1.1, r * 0.6, r * 0.25);
    ctx.fill();
  } else if (id === 'desayuno') {
    ctx.fillStyle = '#ffffff';
    rr(ctx, -r * 0.55, -r * 0.35, r * 0.85, r * 0.85, r * 0.15);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = r * 0.14;
    ctx.beginPath();
    ctx.arc(r * 0.35, r * 0.05, r * 0.22, -1.2, 1.2);
    ctx.stroke();
    blob(-r * 0.12, -r * 0.3, r * 0.3, r * 0.08, '#7a3e1d');
  }
  ctx.restore();
}

function drawHeader(ctx, x, y, w, h, sec) {
  const col = '#' + sec.color.toString(16).padStart(6, '0');
  ctx.save();
  ctx.fillStyle = '#5b3415';
  rr(ctx, x + 6, y + 10, w - 12, h - 14, 34);
  ctx.fill();
  ctx.fillStyle = col;
  rr(ctx, x + 6, y + 4, w - 12, h - 18, 34);
  ctx.fill();
  ctx.setLineDash([14, 10]);
  ctx.lineWidth = 4;
  ctx.strokeStyle = 'rgba(255,255,255,0.75)';
  rr(ctx, x + 18, y + 16, w - 36, h - 42, 24);
  ctx.stroke();
  ctx.setLineDash([]);
  // medallón del icono
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.beginPath();
  ctx.arc(x + 82, y + h / 2 - 7, 46, 0, Math.PI * 2);
  ctx.fill();
  drawSectionIcon(ctx, sec.id, x + 82, y + h / 2 - 5, 38);
  const s = fitText(ctx, sec.title, w - 180, 74);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const tx = x + 140 + (w - 160) / 2 - 10;
  const ty = y + h / 2 - 4;
  ctx.lineJoin = 'round';
  ctx.lineWidth = 12;
  ctx.strokeStyle = '#fff8ec';
  ctx.strokeText(sec.title, tx, ty);
  ctx.fillStyle = sec.ink;
  ctx.fillText(sec.title, tx, ty);
  ctx.restore();
  return s;
}

function drawTag(ctx, x, y, w, h, cents) {
  ctx.save();
  ctx.fillStyle = '#ffe14d';
  rr(ctx, x + 4, y + 4, w - 8, h - 8, 10);
  ctx.fill();
  ctx.fillStyle = '#e63946';
  rr(ctx, x + 4, y + 4, 18, h - 8, 8);
  ctx.fill();
  const txt = soles(cents);
  fitText(ctx, txt, w - 36, 32);
  ctx.fillStyle = '#3a2210';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(txt, x + 14 + w / 2, y + h / 2 + 2);
  ctx.restore();
}

function drawBigSign(ctx, x, y, w, h) {
  ctx.save();
  ctx.fillStyle = '#5b3415';
  rr(ctx, x + 8, y + 16, w - 16, h - 20, 60);
  ctx.fill();
  ctx.fillStyle = '#fff3dc';
  rr(ctx, x + 8, y + 6, w - 16, h - 24, 60);
  ctx.fill();
  ctx.setLineDash([18, 12]);
  ctx.lineWidth = 6;
  ctx.strokeStyle = '#d3893e';
  rr(ctx, x + 26, y + 22, w - 52, h - 58, 44);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  fitText(ctx, 'MERCADITO', w - 120, 104);
  ctx.fillStyle = '#e07a2e';
  ctx.fillText('MERCADITO', x + w / 2, y + h * 0.4 + 4);
  ctx.fillStyle = '#5b3415';
  ctx.fillText('MERCADITO', x + w / 2, y + h * 0.4);
  fitText(ctx, 'Juan Pablo II · Piura', w - 200, 40, 800);
  ctx.fillStyle = '#8a5a2b';
  ctx.fillText('Juan Pablo II · Piura', x + w / 2, y + h * 0.74);
  ctx.restore();
}

function drawPill(ctx, x, y, w, h, text, bg, ink, sub) {
  ctx.save();
  ctx.fillStyle = '#5b3415';
  rr(ctx, x + 6, y + 12, w - 12, h - 16, h * 0.3);
  ctx.fill();
  ctx.fillStyle = bg;
  rr(ctx, x + 6, y + 4, w - 12, h - 18, h * 0.3);
  ctx.fill();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  fitText(ctx, text, w - 40, sub ? 64 : 80);
  ctx.fillStyle = ink;
  ctx.fillText(text, x + w / 2, y + (sub ? h * 0.36 : h / 2 - 6));
  if (sub) {
    fitText(ctx, sub, w - 50, 26, 800);
    ctx.fillText(sub, x + w / 2, y + h * 0.7);
  }
  ctx.restore();
}

function drawPoster(ctx, x, y, w, h, kind) {
  ctx.save();
  ctx.fillStyle = '#fff3dc';
  rr(ctx, x + 6, y + 6, w - 12, h - 12, 20);
  ctx.fill();
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  if (kind === 0) {
    ctx.fillStyle = '#e63946';
    rr(ctx, x + 20, y + 20, w - 40, 70, 14);
    ctx.fill();
    fitText(ctx, '¡OFERTA!', w - 60, 46);
    ctx.fillStyle = '#fff';
    ctx.fillText('¡OFERTA!', x + w / 2, y + 56);
    ctx.fillStyle = '#ffb22e';
    ctx.beginPath();
    ctx.arc(x + w / 2, y + 160, 56, 0, Math.PI * 2);
    ctx.fill();
    fitText(ctx, '2x1', 90, 52);
    ctx.fillStyle = '#5b3415';
    ctx.fillText('2x1', x + w / 2, y + 162);
  } else if (kind === 1) {
    ctx.fillStyle = '#7cc36b';
    ctx.beginPath();
    ctx.arc(x + w / 2, y + 110, 70, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#e24a3b';
    ctx.beginPath();
    ctx.arc(x + w / 2 - 20, y + 116, 34, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#ffb22e';
    ctx.beginPath();
    ctx.arc(x + w / 2 + 26, y + 104, 28, 0, Math.PI * 2);
    ctx.fill();
    fitText(ctx, 'Come sano', w - 40, 40);
    ctx.fillStyle = '#2f6b22';
    ctx.fillText('Come sano', x + w / 2, y + 216);
  } else {
    ctx.fillStyle = '#95e7ff';
    rr(ctx, x + 22, y + 22, w - 44, h - 44, 16);
    ctx.fill();
    ctx.fillStyle = '#fff';
    ctx.beginPath();
    ctx.arc(x + w / 2, y + 100, 46, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = '#d3893e';
    ctx.beginPath();
    ctx.arc(x + w / 2, y + 100, 30, 0, Math.PI * 2);
    ctx.fill();
    fitText(ctx, '¡Gracias!', w - 60, 40);
    ctx.fillStyle = '#1d5f7a';
    ctx.fillText('¡Gracias!', x + w / 2, y + 196);
  }
  ctx.restore();
}

export function buildSignAtlas() {
  const c = canvas(SA_W, SA_H);
  const ctx = c.getContext('2d');
  ctx.clearRect(0, 0, SA_W, SA_H);
  const uv = (px, py, w, h, inset = 2) => ({
    x: (px + inset) / SA_W,
    y: 1 - (py + h - inset) / SA_H,
    w: (w - inset * 2) / SA_W,
    h: (h - inset * 2) / SA_H,
  });
  const headers = {};
  SECTIONS.forEach((sec, i) => {
    const px = (i % 4) * 512;
    const py = Math.floor(i / 4) * 160;
    drawHeader(ctx, px, py, 512, 160, sec);
    headers[sec.id] = uv(px, py, 512, 160);
  });
  const tags = {};
  let k = 0;
  SECTIONS.forEach((sec) =>
    sec.items.forEach((id) => {
      const px = (k % 16) * 128;
      const py = 320 + Math.floor(k / 16) * 64;
      drawTag(ctx, px, py, 128, 64, PRODUCT_BY_ID[id].price);
      tags[id] = uv(px, py, 128, 64);
      k++;
    }),
  );
  drawBigSign(ctx, 0, 512, 1024, 256);
  drawPill(ctx, 1024, 512, 384, 160, 'CAJA', '#95e7ff', '#1d4f6a', 'paga aquí');
  drawPill(ctx, 1408, 512, 384, 160, 'CERRADO', '#ffd28f', '#8a5a2b');
  drawPoster(ctx, 1024, 704, 256, 256, 0);
  drawPoster(ctx, 1280, 704, 256, 256, 1);
  drawPoster(ctx, 1536, 704, 256, 256, 2);
  drawPill(ctx, 0, 800, 512, 160, 'ENTRADA', '#8fc4b8', '#1f4f45');
  const tex = texFrom(c, { aniso: 8 });
  return {
    tex,
    headers,
    tags,
    big: uv(0, 512, 1024, 256),
    caja: uv(1024, 512, 384, 160),
    closed: uv(1408, 512, 384, 160),
    posters: [uv(1024, 704, 256, 256), uv(1280, 704, 256, 256), uv(1536, 704, 256, 256)],
    entrada: uv(0, 800, 512, 160),
  };
}

/* ---------------------------------------------------------------- piso */

/** footprints: rectángulos {x0,z0,x1,z1,ao} sobre los que se hornea sombra de contacto. */
export function buildFloorTexture(footprints) {
  const W = 2048;
  const sx = W / (STORE.x1 - STORE.x0);
  const H = Math.round((STORE.z1 - STORE.z0) * sx);
  const c = canvas(W, H);
  const ctx = c.getContext('2d');
  const X = (x) => (x - STORE.x0) * sx;
  const Z = (z) => (z - STORE.z0) * sx;
  // baldosas
  const tile = 0.8 * sx;
  for (let j = 0; j * tile < H; j++) {
    for (let i = 0; i * tile < W; i++) {
      ctx.fillStyle = (i + j) % 2 ? '#f6e3bf' : '#fbecd0';
      ctx.fillRect(i * tile, j * tile, tile + 1, tile + 1);
    }
  }
  ctx.strokeStyle = 'rgba(190,140,80,0.35)';
  ctx.lineWidth = 2;
  for (let i = 0; i * tile < W; i++) {
    ctx.beginPath();
    ctx.moveTo(i * tile, 0);
    ctx.lineTo(i * tile, H);
    ctx.stroke();
  }
  for (let j = 0; j * tile < H; j++) {
    ctx.beginPath();
    ctx.moveTo(0, j * tile);
    ctx.lineTo(W, j * tile);
    ctx.stroke();
  }
  // zona de frutas: piso de madera cálida
  ctx.fillStyle = 'rgba(160,200,120,0.28)';
  rr(ctx, X(-11.2), Z(1.8), (7.6) * sx, 3.8 * sx, 30);
  ctx.fill();
  // camino suave hacia la caja
  ctx.save();
  ctx.setLineDash([26, 22]);
  ctx.lineWidth = 12;
  ctx.lineCap = 'round';
  ctx.strokeStyle = 'rgba(143,196,184,0.65)';
  ctx.beginPath();
  ctx.moveTo(X(-1), Z(2.2));
  ctx.quadraticCurveTo(X(1.5), Z(2.4), X(CHECKOUT.padX), Z(CHECKOUT.padZ - 1.2));
  ctx.stroke();
  ctx.restore();
  // plataforma de la caja
  ctx.save();
  ctx.fillStyle = 'rgba(149,231,255,0.45)';
  rr(ctx, X(CHECKOUT.padX - 1.0), Z(CHECKOUT.padZ - 1.3), 2.0 * sx, 3.0 * sx, 36);
  ctx.fill();
  ctx.setLineDash([22, 14]);
  ctx.lineWidth = 8;
  ctx.strokeStyle = '#3e9fbf';
  rr(ctx, X(CHECKOUT.padX - 0.9), Z(CHECKOUT.padZ - 1.2), 1.8 * sx, 2.8 * sx, 30);
  ctx.stroke();
  ctx.restore();
  // alfombra de entrada
  ctx.fillStyle = '#c96f2e';
  rr(ctx, X(-8.4), Z(7.2), 3.6 * sx, 1.2 * sx, 20);
  ctx.fill();
  ctx.fillStyle = '#e8924b';
  rr(ctx, X(-8.25), Z(7.32), 3.3 * sx, 0.96 * sx, 16);
  ctx.fill();
  ctx.fillStyle = '#fff3dc';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  fitText(ctx, 'BIENVENIDOS', 3.0 * sx, 0.5 * sx);
  ctx.fillText('BIENVENIDOS', X(-6.6), Z(7.82));
  // sombra de contacto (AO) bajo muebles
  ctx.save();
  try {
    ctx.filter = 'blur(14px)';
  } catch (e) {
    /* sin filtro: sombra dura */
  }
  for (const f of footprints) {
    ctx.fillStyle = `rgba(110,60,20,${f.ao ?? 0.32})`;
    const g = f.grow ?? 0.18;
    rr(ctx, X(f.x0 - g), Z(f.z0 - g), (f.x1 - f.x0 + g * 2) * sx, (f.z1 - f.z0 + g * 2) * sx, 18);
    ctx.fill();
  }
  ctx.restore();
  // viñeta suave hacia los bordes del piso
  const grd = ctx.createRadialGradient(W / 2, H / 2, H * 0.35, W / 2, H / 2, W * 0.62);
  grd.addColorStop(0, 'rgba(0,0,0,0)');
  grd.addColorStop(1, 'rgba(140,80,30,0.16)');
  ctx.fillStyle = grd;
  ctx.fillRect(0, 0, W, H);
  return texFrom(c, { aniso: 8 });
}

/* ---------------------------------------------------------------- detalles */

export function buildBeltTexture() {
  const c = canvas(64, 64);
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#3b3340';
  ctx.fillRect(0, 0, 64, 64);
  ctx.fillStyle = '#4c4352';
  for (let i = 0; i < 4; i++) ctx.fillRect(0, i * 16, 64, 7);
  return texFrom(c, { repeat: true, aniso: 2 });
}

export function buildBlobTexture() {
  const c = canvas(128, 128);
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(90,45,15,0.55)');
  g.addColorStop(0.5, 'rgba(90,45,15,0.28)');
  g.addColorStop(1, 'rgba(90,45,15,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c);
  return t;
}

export function buildRingTexture() {
  const c = canvas(128, 128);
  const ctx = c.getContext('2d');
  ctx.lineWidth = 10;
  ctx.strokeStyle = '#ffffff';
  ctx.setLineDash([18, 12]);
  ctx.beginPath();
  ctx.arc(64, 64, 52, 0, Math.PI * 2);
  ctx.stroke();
  const t = new THREE.CanvasTexture(c);
  return t;
}

/** Pantalla de la registradora: se redibuja cuando cambia el total. */
export class RegisterScreen {
  constructor() {
    this.c = canvas(256, 128);
    this.ctx = this.c.getContext('2d');
    this.tex = texFrom(this.c, { aniso: 2 });
    this.show('¡Hola!', '');
  }
  show(big, small) {
    const ctx = this.ctx;
    ctx.fillStyle = '#1f3b2c';
    ctx.fillRect(0, 0, 256, 128);
    ctx.fillStyle = '#9ff0b8';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    fitText(ctx, big, 236, 56);
    ctx.fillText(big, 128, small ? 52 : 64);
    if (small) {
      fitText(ctx, small, 236, 26, 800);
      ctx.fillStyle = '#c9ffd9';
      ctx.fillText(small, 128, 100);
    }
    this.tex.needsUpdate = true;
  }
}
