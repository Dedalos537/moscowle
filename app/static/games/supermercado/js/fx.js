/*
 * Efectos: confeti y destellos. Partículas en InstancedMesh con arreglos preasignados
 * (sin crear objetos por frame).
 */
import * as THREE from 'three';

const _m = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _e = new THREE.Euler();
const _v = new THREE.Vector3();
const _s = new THREE.Vector3();
const _c = new THREE.Color();

const COLORS = [0xd389ff, 0x95e7ff, 0xffd28f, 0xe63946, 0x7cc36b, 0xffb22e, 0xffffff];

export class Particles {
  constructor(scene, max = 260) {
    this.max = max;
    const geo = new THREE.PlaneGeometry(1, 1);
    const mat = new THREE.MeshBasicMaterial({ side: THREE.DoubleSide, toneMapped: false });
    this.mesh = new THREE.InstancedMesh(geo, mat, max);
    this.mesh.count = 0;
    this.mesh.frustumCulled = false;
    this.mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    scene.add(this.mesh);
    this.p = new Float32Array(max * 3);
    this.v = new Float32Array(max * 3);
    this.r = new Float32Array(max * 3);
    this.w = new Float32Array(max * 3);
    this.life = new Float32Array(max);
    this.size = new Float32Array(max);
    this.drag = new Float32Array(max);
    this.grav = new Float32Array(max);
    this.n = 0;
    this.vecs = [this.p, this.v, this.r, this.w];
    for (let i = 0; i < max; i++) this.mesh.setColorAt(i, _c.set(0xffffff));
  }

  spawn(x, y, z, vx, vy, vz, size, life, color, grav = 9.8, drag = 1.2) {
    if (this.n >= this.max) return;
    const i = this.n++;
    this.p[i * 3] = x;
    this.p[i * 3 + 1] = y;
    this.p[i * 3 + 2] = z;
    this.v[i * 3] = vx;
    this.v[i * 3 + 1] = vy;
    this.v[i * 3 + 2] = vz;
    this.r[i * 3] = Math.random() * 6;
    this.r[i * 3 + 1] = Math.random() * 6;
    this.r[i * 3 + 2] = Math.random() * 6;
    this.w[i * 3] = (Math.random() - 0.5) * 14;
    this.w[i * 3 + 1] = (Math.random() - 0.5) * 14;
    this.w[i * 3 + 2] = (Math.random() - 0.5) * 14;
    this.life[i] = life;
    this.size[i] = size;
    this.grav[i] = grav;
    this.drag[i] = drag;
    this.mesh.setColorAt(i, _c.set(color));
    this.mesh.instanceColor.needsUpdate = true;
  }

  confetti(x, y, z, count = 120, spread = 2.5) {
    for (let i = 0; i < count; i++) {
      const a = Math.random() * Math.PI * 2;
      const sp = 1.5 + Math.random() * spread;
      this.spawn(x, y, z, Math.cos(a) * sp, 4 + Math.random() * 4.5, Math.sin(a) * sp, 0.07 + Math.random() * 0.06, 2.4 + Math.random() * 1.2, COLORS[i % COLORS.length], 6, 1.6);
    }
  }

  sparkle(x, y, z, color = 0xfff3a0, count = 10) {
    for (let i = 0; i < count; i++) {
      const a = (i / count) * Math.PI * 2;
      this.spawn(x, y, z, Math.cos(a) * 1.6, 1.2 + Math.random() * 1.2, Math.sin(a) * 1.6, 0.06, 0.5 + Math.random() * 0.2, color, 3, 3);
    }
  }

  update(dt) {
    let i = 0;
    while (i < this.n) {
      this.life[i] -= dt;
      if (this.life[i] <= 0) {
        // compacta: mueve la última al hueco
        const last = --this.n;
        if (i !== last) {
          for (let a = 0; a < 4; a++) {
            const arr = this.vecs[a];
            arr[i * 3] = arr[last * 3];
            arr[i * 3 + 1] = arr[last * 3 + 1];
            arr[i * 3 + 2] = arr[last * 3 + 2];
          }
          this.life[i] = this.life[last];
          this.size[i] = this.size[last];
          this.grav[i] = this.grav[last];
          this.drag[i] = this.drag[last];
          this.mesh.getColorAt(last, _c);
          this.mesh.setColorAt(i, _c);
          this.mesh.instanceColor.needsUpdate = true;
        }
        continue;
      }
      const k = Math.exp(-this.drag[i] * dt);
      this.v[i * 3] *= k;
      this.v[i * 3 + 2] *= k;
      this.v[i * 3 + 1] = this.v[i * 3 + 1] * k - this.grav[i] * dt;
      this.p[i * 3] += this.v[i * 3] * dt;
      this.p[i * 3 + 1] += this.v[i * 3 + 1] * dt;
      this.p[i * 3 + 2] += this.v[i * 3 + 2] * dt;
      if (this.p[i * 3 + 1] < 0.02) {
        this.p[i * 3 + 1] = 0.02;
        this.v[i * 3 + 1] = 0;
        this.v[i * 3] *= 0.5;
        this.v[i * 3 + 2] *= 0.5;
      }
      this.r[i * 3] += this.w[i * 3] * dt;
      this.r[i * 3 + 1] += this.w[i * 3 + 1] * dt;
      this.r[i * 3 + 2] += this.w[i * 3 + 2] * dt;
      _e.set(this.r[i * 3], this.r[i * 3 + 1], this.r[i * 3 + 2]);
      _q.setFromEuler(_e);
      const s = this.size[i] * Math.min(1, this.life[i] * 3);
      _s.set(s, s * 0.6, s);
      _m.compose(_v.set(this.p[i * 3], this.p[i * 3 + 1], this.p[i * 3 + 2]), _q, _s);
      this.mesh.setMatrixAt(i, _m);
      i++;
    }
    this.mesh.count = this.n;
    this.mesh.instanceMatrix.needsUpdate = true;
  }

  clear() {
    this.n = 0;
    this.mesh.count = 0;
  }
}
