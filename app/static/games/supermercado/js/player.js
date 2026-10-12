/*
 * El niño con su carrito: movimiento con inercia, giro con resorte (el carrito "pesa"),
 * colisiones contra muebles (dos círculos: cuerpo y carrito) y pequeños choques suaves.
 */
import * as THREE from 'three';
import { Character, Cart, LOOKS } from './actors.js';
import { Spring, clamp, angleDiff } from './util.js';

const CART_OFF = 0.7;

export class Player {
  constructor(scene, mat) {
    this.group = new THREE.Group();
    this.char = new Character(LOOKS.player, mat);
    this.cart = new Cart(mat, 0xd389ff, 0xffd28f);
    this.cart.group.position.set(0, 0, CART_OFF);
    this.group.add(this.char.root, this.cart.group);
    scene.add(this.group);
    this.pos = new THREE.Vector2();
    this.vel = new THREE.Vector2();
    this.heading = Math.PI;
    this.angVel = 0;
    this.speed = 0;
    this.fwdAccel = 0;
    this.bumpCooldown = 0;
    this.onBump = null;
    this.calm = false;
    this.auto = null; // movimiento automático (estacionarse en la caja)
    this.cartWorld = new THREE.Vector2();
    this.r1 = 0.3;
    this.r2 = 0.43;
  }

  place(x, z, heading) {
    this.pos.set(x, z);
    this.vel.set(0, 0);
    this.heading = heading;
    this.angVel = 0;
    this.speed = 0;
    this.sync(0);
  }

  get fx() {
    return Math.sin(this.heading);
  }
  get fz() {
    return Math.cos(this.heading);
  }

  /**
   * move: vector de entrada en el plano (x→este, y→sur). colliders: AABBs. others: círculos móviles.
   */
  update(dt, move, run, colliders, others) {
    const maxS = (run ? 5.0 : 3.3) * (this.calm ? 0.72 : 1);
    let dx = move.x;
    let dz = move.y;
    if (this.auto) {
      const tx = this.auto.x - this.pos.x;
      const tz = this.auto.z - this.pos.y;
      const d = Math.hypot(tx, tz);
      if (d < 0.08) {
        dx = dz = 0;
      } else {
        const k = Math.min(1, d / 1.2);
        dx = (tx / d) * k * 0.7;
        dz = (tz / d) * k * 0.7;
      }
    }
    const len = Math.hypot(dx, dz);
    const tvx = dx * maxS;
    const tvz = dz * maxS;
    // aceleración con inercia: arranca suave y frena un poco más rápido
    const accel = len > 0.05 ? 9 : 12;
    const ax = tvx - this.vel.x;
    const az = tvz - this.vel.y;
    const al = Math.hypot(ax, az);
    const maxDv = accel * dt;
    if (al > maxDv) {
      this.vel.x += (ax / al) * maxDv;
      this.vel.y += (az / al) * maxDv;
    } else {
      this.vel.x = tvx;
      this.vel.y = tvz;
    }
    const prevSpeed = this.speed;
    this.speed = this.vel.length();
    // el rumbo sigue a la velocidad con un resorte (sensación de peso del carrito)
    let want = this.heading;
    if (this.auto && this.auto.heading !== undefined && this.speed < 0.25) want = this.auto.heading;
    else if (this.speed > 0.15) want = Math.atan2(this.vel.x, this.vel.y);
    let diff = angleDiff(this.heading, want);
    // contra una pared el carrito no se retuerce: el giro se calma
    if (this.pinned > 0) {
      diff *= 0.15;
      this.angVel *= 0.8;
    }
    const k = 46;
    const c = 12.5;
    this.angVel += (diff * k - this.angVel * c) * dt;
    this.angVel = clamp(this.angVel, -7, 7);
    this.heading += this.angVel * dt;
    // si el carrito apunta muy distinto a la velocidad, se frena un poco (no se desliza de lado)
    if (this.speed > 0.2) {
      const align = Math.cos(diff);
      if (align < 0.5) this.vel.multiplyScalar(1 - clamp((0.5 - align) * 0.8, 0, 0.6) * dt * 4);
    }
    this.pos.x += this.vel.x * dt;
    this.pos.y += this.vel.y * dt;
    this.pinned = Math.max(0, (this.pinned || 0) - dt);
    if (!this.auto) this.resolve(colliders, others);
    this.fwdAccel = (this.speed - prevSpeed) / Math.max(dt, 1e-4);
    this.bumpCooldown -= dt;
    this.sync(dt);
  }

  /** Empuja los dos círculos (cuerpo y carrito) fuera de los obstáculos. */
  resolve(colliders, others) {
    for (let it = 0; it < 2; it++) {
      for (let pass = 0; pass < 2; pass++) {
        const off = pass === 0 ? 0 : CART_OFF;
        const r = pass === 0 ? this.r1 : this.r2;
        const cx = this.pos.x + this.fx * off;
        const cz = this.pos.y + this.fz * off;
        for (const b of colliders) {
          const px = clamp(cx, b.x0, b.x1);
          const pz = clamp(cz, b.z0, b.z1);
          let nx = cx - px;
          let nz = cz - pz;
          const d2 = nx * nx + nz * nz;
          if (d2 >= r * r) continue;
          let d = Math.sqrt(d2);
          if (d < 1e-5) {
            // centro dentro de la caja: sale por el lado más cercano
            const l = cx - b.x0;
            const rr = b.x1 - cx;
            const t = cz - b.z0;
            const bt = b.z1 - cz;
            const m = Math.min(l, rr, t, bt);
            nx = m === l ? -1 : m === rr ? 1 : 0;
            nz = m === t ? -1 : m === bt ? 1 : 0;
            d = -m;
          } else {
            nx /= d;
            nz /= d;
          }
          const push = r - d;
          this.pos.x += nx * push;
          this.pos.y += nz * push;
          const vn = this.vel.x * nx + this.vel.y * nz;
          if (vn < 0) {
            if (vn < -2.2 && this.bumpCooldown <= 0) {
              this.bumpCooldown = 0.5;
              this.onBump && this.onBump(-vn);
            }
            // quita solo la componente contra la pared: el carrito se desliza a lo largo
            const k = vn < -2.2 ? 1.12 : 1.0;
            this.vel.x -= nx * vn * k;
            this.vel.y -= nz * vn * k;
            if (pass === 1) this.pinned = 0.15;
          }
        }
        if (others) {
          for (const o of others) {
            const ox = cx - o.x;
            const oz = cz - o.z;
            const rr = r + o.r;
            const d2 = ox * ox + oz * oz;
            if (d2 >= rr * rr || d2 < 1e-6) continue;
            const d = Math.sqrt(d2);
            const push = rr - d;
            this.pos.x += (ox / d) * push;
            this.pos.y += (oz / d) * push;
            const vn = (this.vel.x * ox + this.vel.y * oz) / d;
            if (vn < 0) {
              this.vel.x -= (ox / d) * vn;
              this.vel.y -= (oz / d) * vn;
            }
          }
        }
      }
    }
  }

  sync(dt) {
    this.group.position.set(this.pos.x, 0, this.pos.y);
    this.group.rotation.y = this.heading;
    this.cartWorld.set(this.pos.x + this.fx * CART_OFF, this.pos.y + this.fz * CART_OFF);
    if (dt > 0) {
      this.char.update(dt, this.speed, this.fwdAccel, this.angVel);
      const cart = this.cart;
      cart.spin += (this.speed * dt) / 0.06;
      // el carrito se balancea y se inclina en las curvas
      cart.yaw.target = clamp(-this.angVel * 0.06, -0.25, 0.25);
      cart.rollS.target = clamp(this.angVel * 0.03 * Math.min(1, this.speed / 2), -0.08, 0.08);
      cart.pivot.rotation.y = cart.yaw.step(dt);
      cart.pivot.rotation.z = cart.rollS.step(dt);
      cart.pivot.rotation.x = cart.bump.step(dt) + clamp(-this.fwdAccel * 0.004, -0.03, 0.03);
    }
  }
}

export { CART_OFF };
