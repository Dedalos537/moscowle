/*
 * Entrada unificada: teclado, joystick táctil, botón de acción grande, mando (gamepad) y puntero.
 * El juego consulta move (vector en pantalla), run, y los "pulsos" de acción.
 */
import { clamp } from './util.js';

export class Input {
  constructor(el) {
    this.el = el;
    this.keys = new Set();
    this.move = { x: 0, y: 0 };
    this.run = false;
    this.pulses = { action: false, pause: false, back: false, peek: false };
    this.stick = { active: false, id: -1, ox: 0, oy: 0, x: 0, y: 0 };
    this.touchMode = matchMedia('(pointer: coarse)').matches;
    this.gpPrev = {};
    this.enabled = true;
    this.onTouchMode = null;

    addEventListener('keydown', (e) => {
      if (e.target && /INPUT|TEXTAREA|SELECT/.test(e.target.tagName)) return;
      const k = e.code;
      if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Space'].includes(k)) e.preventDefault();
      if (!e.repeat) {
        if (k === 'KeyE' || k === 'Space' || k === 'Enter' || k === 'NumpadEnter') this.pulses.action = true;
        if (k === 'Escape' || k === 'KeyP') this.pulses.pause = true;
        if (k === 'KeyR' || k === 'Backspace') this.pulses.back = true;
        if (k === 'KeyL' || k === 'Tab') {
          this.pulses.peek = true;
          if (k === 'Tab') e.preventDefault();
        }
      }
      this.keys.add(k);
      this.setTouch(false);
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());

    // joystick táctil dinámico: aparece donde se apoya el pulgar (mitad izquierda)
    const zone = document.getElementById('stickZone');
    const base = document.getElementById('stickBase');
    const knob = document.getElementById('stickKnob');
    this.stickEls = { zone, base, knob };
    zone.addEventListener('pointerdown', (e) => {
      if (this.stick.active) return;
      e.preventDefault();
      this.setTouch(true);
      zone.setPointerCapture(e.pointerId);
      const r = zone.getBoundingClientRect();
      this.stick.active = true;
      this.stick.id = e.pointerId;
      this.stick.ox = clamp(e.clientX, r.left + 60, r.right - 60);
      this.stick.oy = clamp(e.clientY, r.top + 60, r.bottom - 60);
      this.stick.x = this.stick.y = 0;
      base.style.transform = `translate(${this.stick.ox - r.left - 60}px, ${this.stick.oy - r.top - 60}px)`;
      base.classList.add('on');
      this.updateKnob();
    });
    zone.addEventListener('pointermove', (e) => {
      if (!this.stick.active || e.pointerId !== this.stick.id) return;
      const dx = e.clientX - this.stick.ox;
      const dy = e.clientY - this.stick.oy;
      const len = Math.hypot(dx, dy);
      const max = 52;
      const k = len > max ? max / len : 1;
      this.stick.x = (dx * k) / max;
      this.stick.y = (dy * k) / max;
      this.updateKnob();
    });
    const end = (e) => {
      if (e.pointerId !== this.stick.id) return;
      this.stick.active = false;
      this.stick.id = -1;
      this.stick.x = this.stick.y = 0;
      base.classList.remove('on');
      base.style.transform = '';
      this.updateKnob();
    };
    zone.addEventListener('pointerup', end);
    zone.addEventListener('pointercancel', end);

    const act = document.getElementById('actBtn');
    act.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      this.setTouch(true);
      this.pulses.action = true;
      act.classList.add('down');
    });
    const up = () => act.classList.remove('down');
    act.addEventListener('pointerup', up);
    act.addEventListener('pointercancel', up);
    act.addEventListener('pointerleave', up);
    addEventListener('touchstart', () => this.setTouch(true), { passive: true });
  }

  setTouch(on) {
    if (this.touchMode === on) return;
    this.touchMode = on;
    this.onTouchMode && this.onTouchMode(on);
  }

  updateKnob() {
    const { knob } = this.stickEls;
    knob.style.transform = `translate(${this.stick.x * 52}px, ${this.stick.y * 52}px)`;
  }

  /** Lee el estado del frame. Devuelve el vector de movimiento (x→derecha, y→abajo en pantalla). */
  poll() {
    let x = 0;
    let y = 0;
    const k = this.keys;
    if (k.has('KeyA') || k.has('ArrowLeft')) x -= 1;
    if (k.has('KeyD') || k.has('ArrowRight')) x += 1;
    if (k.has('KeyW') || k.has('ArrowUp')) y -= 1;
    if (k.has('KeyS') || k.has('ArrowDown')) y += 1;
    let run = k.has('ShiftLeft') || k.has('ShiftRight');
    if (this.stick.active) {
      x += this.stick.x;
      y += this.stick.y;
      run = run || Math.hypot(this.stick.x, this.stick.y) > 0.96;
    }
    // mando
    const pads = navigator.getGamepads ? navigator.getGamepads() : [];
    for (const gp of pads) {
      if (!gp) continue;
      const ax = gp.axes[0] || 0;
      const ay = gp.axes[1] || 0;
      if (Math.hypot(ax, ay) > 0.18) {
        x += ax;
        y += ay;
      }
      const b = (i) => gp.buttons[i] && gp.buttons[i].pressed;
      const edge = (name, now) => {
        const was = this.gpPrev[name];
        this.gpPrev[name] = now;
        return now && !was;
      };
      if (edge('a', b(0))) this.pulses.action = true;
      if (edge('b', b(1))) this.pulses.back = true;
      if (edge('y', b(3))) this.pulses.peek = true;
      if (edge('start', b(9))) this.pulses.pause = true;
      if (b(7) || b(5)) run = true;
      if (b(12)) y -= 1;
      if (b(13)) y += 1;
      if (b(14)) x -= 1;
      if (b(15)) x += 1;
    }
    const len = Math.hypot(x, y);
    if (len > 1) {
      x /= len;
      y /= len;
    }
    if (!this.enabled) x = y = 0;
    this.move.x = x;
    this.move.y = y;
    this.run = run;
    return this.move;
  }

  take(name) {
    const v = this.pulses[name];
    this.pulses[name] = false;
    return v;
  }

  clearPulses() {
    for (const k in this.pulses) this.pulses[k] = false;
  }
}
