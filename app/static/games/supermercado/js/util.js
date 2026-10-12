/* Utilidades sin dependencias: resortes, curvas, azar con semilla, tweens y almacenamiento seguro. */

export const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
export const lerp = (a, b, t) => a + (b - a) * t;
export const smooth = (t) => t * t * (3 - 2 * t);
export const easeOutCubic = (t) => 1 - Math.pow(1 - t, 3);
export const easeInOutCubic = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
export const easeOutBack = (t, s = 1.70158) => 1 + (s + 1) * Math.pow(t - 1, 3) + s * Math.pow(t - 1, 2);

/** Diferencia angular más corta (rad). */
export function angleDiff(a, b) {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
}

/** Amortiguamiento exponencial independiente del frame rate. */
export function damp(current, target, lambda, dt) {
  return lerp(current, target, 1 - Math.exp(-lambda * dt));
}

/**
 * Resorte críticamente amortiguado escalar (estable con dt variable).
 * Se usa para cámara, inclinaciones y rebotes: da movimiento suave sin oscilar de más.
 */
export class Spring {
  constructor(value = 0, omega = 8, zeta = 1) {
    this.x = value;
    this.v = 0;
    this.target = value;
    this.omega = omega;
    this.zeta = zeta;
  }
  step(dt) {
    // integración semi-implícita en sub-pasos para robustez
    const n = dt > 1 / 60 ? Math.ceil(dt * 120) : 1;
    const h = dt / n;
    const w = this.omega;
    const z = this.zeta;
    for (let i = 0; i < n; i++) {
      const a = -2 * z * w * this.v - w * w * (this.x - this.target);
      this.v += a * h;
      this.x += this.v * h;
    }
    return this.x;
  }
  snap(v) {
    this.x = this.target = v;
    this.v = 0;
  }
}

/** Generador con semilla (mulberry32). */
export function rng(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

export function shuffle(arr, rand) {
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    const t = arr[i];
    arr[i] = arr[j];
    arr[j] = t;
  }
  return arr;
}

/**
 * Tweens simples por tiempo de juego. Cada tween llama a fn(t) con t en [0,1] ya suavizado.
 * Se usa para secuencias (caja registradora, vuelos de producto devuelto...).
 */
export class Tweens {
  constructor() {
    this.list = [];
    this.scale = 1;
  }
  add(duration, fn, { ease = easeInOutCubic, delay = 0, done = null } = {}) {
    const tw = { t: -delay, d: Math.max(0.0001, duration), fn, ease, done, dead: false };
    this.list.push(tw);
    return tw;
  }
  wait(seconds) {
    return new Promise((res) => this.add(seconds, () => {}, { done: res }));
  }
  to(duration, fn, opts = {}) {
    return new Promise((res) => {
      const prev = opts.done;
      this.add(duration, fn, { ...opts, done: () => { prev && prev(); res(); } });
    });
  }
  update(dt) {
    dt *= this.scale;
    const l = this.list;
    for (let i = 0; i < l.length; i++) {
      const tw = l[i];
      if (tw.dead) continue;
      tw.t += dt;
      if (tw.t < 0) continue;
      const k = Math.min(1, tw.t / tw.d);
      tw.fn(tw.ease(k), k);
      if (k >= 1) {
        tw.dead = true;
        tw.done && tw.done();
      }
    }
    if (l.length > 32) this.list = l.filter((tw) => !tw.dead);
  }
  clear() {
    this.list.length = 0;
  }
}

export const store = {
  get(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (e) {
      return fallback;
    }
  },
  set(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
      /* sin almacenamiento: el juego sigue igual */
    }
  },
};
