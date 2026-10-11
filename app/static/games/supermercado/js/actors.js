/*
 * Personajes animados (jugador, cajera, clientes) y carritos con ruedas que giran.
 * La animación es procedural: ciclo de caminata, rebote, inclinación en curvas, parpadeo.
 */
import * as THREE from 'three';
import { characterGeometries, cartGeometry, wheelGeometry } from './models.js';
import { Spring, clamp, angleDiff } from './util.js';

const _m = new THREE.Matrix4();
const _m2 = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _v = new THREE.Vector3();
const _s = new THREE.Vector3(1, 1, 1);
const X = new THREE.Vector3(1, 0, 0);

const geoCache = new Map();

export class Character {
  constructor(look, mat) {
    const key = JSON.stringify(look);
    if (!geoCache.has(key)) geoCache.set(key, characterGeometries(look));
    const g = geoCache.get(key);
    const mk = (geo) => {
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = true;
      return m;
    };
    this.root = new THREE.Group();
    this.body = new THREE.Group();
    this.root.add(this.body);
    this.hip = 0.355;
    this.legL = mk(g.legL);
    this.legR = mk(g.legR);
    this.legL.position.set(0.09, this.hip, 0);
    this.legR.position.set(-0.09, this.hip, 0);
    this.torso = mk(g.torso);
    this.torso.position.set(0, this.hip - 0.02, 0);
    this.head = new THREE.Group();
    this.head.position.set(0, this.hip + 0.34, 0);
    this.headMesh = mk(g.head);
    this.eyes = mk(g.eyes);
    this.eyes.castShadow = false;
    this.head.add(this.headMesh, this.eyes);
    this.armL = mk(g.armL);
    this.armR = mk(g.armR);
    this.armL.position.set(0.22, this.hip + 0.27, 0);
    this.armR.position.set(-0.22, this.hip + 0.27, 0);
    this.body.add(this.legL, this.legR, this.torso, this.head, this.armL, this.armR);
    this.phase = 0;
    this.blinkT = 2 + Math.random() * 3;
    this.headRoll = new Spring(0, 9, 0.45);
    this.headYaw = new Spring(0, 6, 0.8);
    this.lean = new Spring(0, 10, 0.7);
    this.roll = new Spring(0, 10, 0.6);
    this.armPose = { l: new Spring(0, 12, 0.75), r: new Spring(0, 12, 0.75), lz: new Spring(0, 12, 0.75), rz: new Spring(0, 12, 0.75) };
    this.squash = new Spring(1, 16, 0.35);
    this.time = Math.random() * 10;
    this.pushing = true;
    this.lookYaw = 0;
    this.reduced = false;
  }

  /**
   * st: { speed (m/s), accel (m/s² hacia adelante), turn (rad/s), dt }
   * Los brazos se manejan con setArms() cuando no empuja un carrito.
   */
  update(dt, speed, accel, turn) {
    this.time += dt;
    const amp = clamp(speed / 3, 0, 1);
    this.phase += dt * (4 + speed * 3.4) * (amp > 0.02 ? 1 : 0);
    const sw = Math.sin(this.phase);
    const motion = this.reduced ? 0.5 : 1;
    // piernas y rebote
    this.legL.rotation.x = sw * 0.75 * amp;
    this.legR.rotation.x = -sw * 0.75 * amp;
    const breathe = Math.sin(this.time * 2.2) * 0.008;
    this.body.position.y = Math.abs(Math.cos(this.phase)) * 0.05 * amp * motion + breathe;
    // inclinación: hacia adelante al acelerar, hacia el lado en las curvas
    this.lean.target = clamp(0.05 * speed + accel * 0.025, -0.15, 0.32) * motion;
    this.roll.target = clamp(-turn * 0.09, -0.22, 0.22) * motion;
    this.body.rotation.x = this.lean.step(dt);
    this.body.rotation.z = this.roll.step(dt);
    // la cabeza se queda un poco atrás (resorte poco amortiguado)
    this.headRoll.target = -this.body.rotation.z * 0.6 + sw * 0.03 * amp * motion;
    this.head.rotation.z = this.headRoll.step(dt);
    this.headYaw.target = this.lookYaw;
    this.head.rotation.y = this.headYaw.step(dt);
    this.head.rotation.x = -this.body.rotation.x * 0.5 + Math.sin(this.time * 1.3) * 0.02;
    // brazos
    if (this.pushing) {
      this.armPose.l.target = -1.32 + sw * 0.05 * amp;
      this.armPose.r.target = -1.32 - sw * 0.05 * amp;
      this.armPose.lz.target = 0.18;
      this.armPose.rz.target = -0.18;
    }
    this.armL.rotation.x = this.armPose.l.step(dt);
    this.armR.rotation.x = this.armPose.r.step(dt);
    this.armL.rotation.z = this.armPose.lz.step(dt);
    this.armR.rotation.z = this.armPose.rz.step(dt);
    // aplastado/estirado (al chocar o celebrar)
    const sq = this.squash.step(dt);
    this.body.scale.set(1 + (1 - sq) * 0.5, sq, 1 + (1 - sq) * 0.5);
    // parpadeo
    this.blinkT -= dt;
    if (this.blinkT < 0) {
      this.blinkT = 2.2 + Math.random() * 3.5;
    }
    this.eyes.scale.y = this.blinkT < 0.12 ? 0.15 : 1;
  }

  setArms(l, r, lz = 0.12, rz = -0.12) {
    this.armPose.l.target = l;
    this.armPose.r.target = r;
    this.armPose.lz.target = lz;
    this.armPose.rz.target = rz;
  }

  bounce(amount = 0.25) {
    this.squash.v -= amount * 8;
  }
}

/** Carrito visual. Su contenido se dibuja en el lote de productos (ver game.js). */
export class Cart {
  constructor(mat, color, trim) {
    this.group = new THREE.Group();
    this.pivot = new THREE.Group();
    this.group.add(this.pivot);
    this.mesh = new THREE.Mesh(cartGeometry(color, trim), mat);
    this.mesh.castShadow = true;
    this.mesh.receiveShadow = true;
    this.mesh.position.y = 0.06;
    this.pivot.add(this.mesh);
    this.spin = 0;
    this.wheelOffsets = [
      [0.27, 0.06, 0.2],
      [-0.27, 0.06, 0.2],
      [0.27, 0.06, -0.2],
      [-0.27, 0.06, -0.2],
    ];
    this.yaw = new Spring(0, 7, 0.45);
    this.rollS = new Spring(0, 9, 0.4);
    this.bump = new Spring(0, 14, 0.3);
  }
}

/** Todas las ruedas de todos los carritos en una sola malla instanciada. */
export class Wheels {
  constructor(scene, mat, max = 16) {
    this.mesh = new THREE.InstancedMesh(wheelGeometry(), mat, max);
    this.mesh.castShadow = true;
    this.mesh.count = 0;
    this.mesh.frustumCulled = false;
    scene.add(this.mesh);
  }
  update(carts) {
    let i = 0;
    for (const cart of carts) {
      if (!cart.group.visible || (cart.group.parent && !cart.group.parent.visible)) continue;
      cart.mesh.updateWorldMatrix(true, false);
      for (const o of cart.wheelOffsets) {
        _q.setFromAxisAngle(X, cart.spin);
        _m2.compose(_v.set(o[0], o[1] - 0.06, o[2]), _q, _s);
        _m.multiplyMatrices(cart.mesh.matrixWorld, _m2);
        this.mesh.setMatrixAt(i++, _m);
      }
    }
    this.mesh.count = i;
    this.mesh.instanceMatrix.needsUpdate = true;
  }
}

export const LOOKS = {
  player: { skin: 0xc98d62, hair: 0x3a2418, shirt: 0x8fc4b8, pants: 0x355c8a, shoes: 0xe63946, cap: 0xffb22e, backpack: 0xd389ff },
  cashier: { skin: 0xd9a27a, hair: 0x2a1a12, shirt: 0xfff3dc, pants: 0x5b3415, shoes: 0x3a2a20, apron: 0xd389ff, bun: true },
  shopperA: { skin: 0xe0b08a, hair: 0xd8d8d8, shirt: 0xff9fb2, pants: 0x6b4f8a, shoes: 0x5b3415, bun: true, glasses: true },
  shopperB: { skin: 0xb07a52, hair: 0x1f140e, shirt: 0xffd28f, pants: 0x2f6f62, shoes: 0x3a2a20, cap: 0x3c7be0 },
};

/** Cliente que pasea con su carrito por una ruta (distracción en niveles altos). */
export class Shopper {
  constructor(scene, mat, look, path, color, trim, speed = 1.25) {
    this.char = new Character(look, mat);
    this.char.root.scale.setScalar(1.08);
    this.cart = new Cart(mat, color, trim);
    this.group = new THREE.Group();
    this.group.add(this.char.root);
    this.cart.group.position.set(0, 0, 0.7);
    this.group.add(this.cart.group);
    scene.add(this.group);
    this.path = path;
    this.idx = 1;
    this.pos = new THREE.Vector2(path[0][0], path[0][1]);
    this.heading = 0;
    this.speed = 0;
    this.maxSpeed = speed;
    this.wait = 0;
    this.blocked = 0;
    this.turn = 0;
    this.say = null;
    this.sayT = 0;
    this.active = true;
  }

  reset(i0 = 0) {
    this.idx = (i0 + 1) % this.path.length;
    this.pos.set(this.path[i0][0], this.path[i0][1]);
    const n = this.path[this.idx];
    this.heading = Math.atan2(n[0] - this.pos.x, n[1] - this.pos.y);
    this.speed = 0;
  }

  update(dt, player) {
    const target = this.path[this.idx];
    const dx = target[0] - this.pos.x;
    const dz = target[1] - this.pos.y;
    const dist = Math.hypot(dx, dz);
    if (dist < 0.4) this.idx = (this.idx + 1) % this.path.length;
    const want = Math.atan2(dx, dz);
    const d = angleDiff(this.heading, want);
    const turnRate = clamp(d * 3, -2.2, 2.2);
    this.heading += turnRate * dt;
    this.turn = turnRate;
    // se detiene si el jugador está delante
    const fx = Math.sin(this.heading);
    const fz = Math.cos(this.heading);
    const px = player.pos.x - this.pos.x;
    const pz = player.pos.y - this.pos.y;
    const ahead = px * fx + pz * fz;
    const side = Math.abs(px * fz - pz * fx);
    let desired = this.wait > 0 ? 0 : this.maxSpeed * (Math.abs(d) > 1.2 ? 0.4 : 1);
    if (ahead > 0 && ahead < 2.2 && side < 1.0) {
      desired = 0;
      this.blocked += dt;
      if (this.blocked > 0.35 && this.sayT <= 0) {
        this.say = ['¡Uy, perdón!', '¡Con permiso!', '¡Hola!'][Math.floor(Math.random() * 3)];
        this.sayT = 2.4;
      }
    } else this.blocked = 0;
    this.wait -= dt;
    this.sayT -= dt;
    const prev = this.speed;
    this.speed += clamp(desired - this.speed, -4 * dt, 2.5 * dt);
    this.pos.x += fx * this.speed * dt;
    this.pos.y += fz * this.speed * dt;
    this.group.position.set(this.pos.x, 0, this.pos.y);
    this.group.rotation.y = this.heading;
    this.char.update(dt, this.speed, (this.speed - prev) / Math.max(dt, 1e-4), this.turn);
    this.cart.spin += (this.speed * dt) / 0.06;
    this.cart.yaw.target = -this.turn * 0.05;
    this.cart.pivot.rotation.y = this.cart.yaw.step(dt);
  }
}
