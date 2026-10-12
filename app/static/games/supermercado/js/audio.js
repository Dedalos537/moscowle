/*
 * Sonido sintetizado con WebAudio (sin archivos): efectos suaves y una música alegre de fondo.
 * Se activa con el primer gesto del usuario (política de autoplay de los navegadores).
 */

export class Audio {
  constructor() {
    this.ctx = null;
    this.sfxOn = true;
    this.musicOn = true;
    this.musicTimer = null;
    this.step = 0;
    this.nextTime = 0;
    this.rattle = null;
  }

  unlock() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') this.ctx.resume();
      return;
    }
    const AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    try {
      this.ctx = new AC();
    } catch (e) {
      return;
    }
    const c = this.ctx;
    this.master = c.createGain();
    this.master.gain.value = 0.8;
    this.master.connect(c.destination);
    this.sfx = c.createGain();
    this.sfx.gain.value = this.sfxOn ? 0.55 : 0;
    this.sfx.connect(this.master);
    this.music = c.createGain();
    this.music.gain.value = this.musicOn ? 0.16 : 0;
    this.music.connect(this.master);
    // ruido para el traqueteo del carrito
    const len = c.sampleRate;
    const buf = c.createBuffer(1, len, c.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * 0.6;
    this.noiseBuf = buf;
    const src = c.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const bp = c.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = 900;
    bp.Q.value = 1.4;
    const g = c.createGain();
    g.gain.value = 0;
    src.connect(bp).connect(g).connect(this.sfx);
    src.start();
    this.rattle = { g, bp };
    this.startMusic();
  }

  setSfx(on) {
    this.sfxOn = on;
    if (this.sfx) this.sfx.gain.setTargetAtTime(on ? 0.55 : 0, this.ctx.currentTime, 0.05);
  }

  setMusic(on) {
    this.musicOn = on;
    if (this.music) this.music.gain.setTargetAtTime(on ? 0.16 : 0, this.ctx.currentTime, 0.2);
  }

  suspend(s) {
    if (!this.ctx) return;
    if (s) this.ctx.suspend();
    else this.ctx.resume();
  }

  tone(freq, dur, { type = 'sine', vol = 0.4, slide = 0, delay = 0, attack = 0.005, dest = null } = {}) {
    if (!this.ctx || !this.sfxOn) return;
    const c = this.ctx;
    const t = c.currentTime + delay;
    const o = c.createOscillator();
    const g = c.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq + slide), t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + attack);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(dest || this.sfx);
    o.start(t);
    o.stop(t + dur + 0.05);
  }

  noise(dur, { freq = 1200, q = 1, vol = 0.3, delay = 0 } = {}) {
    if (!this.ctx || !this.sfxOn) return;
    const c = this.ctx;
    const t = c.currentTime + delay;
    const s = c.createBufferSource();
    s.buffer = this.noiseBuf;
    const f = c.createBiquadFilter();
    f.type = 'bandpass';
    f.frequency.value = freq;
    f.Q.value = q;
    const g = c.createGain();
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    s.connect(f).connect(g).connect(this.sfx);
    s.start(t, Math.random() * 0.5);
    s.stop(t + dur + 0.05);
  }

  /* efectos con nombre */
  pick() {
    this.tone(520, 0.16, { type: 'triangle', slide: 520, vol: 0.35 });
    this.tone(1040, 0.08, { type: 'sine', vol: 0.12, delay: 0.05 });
  }
  land(k = 0) {
    this.tone(180 + k * 20, 0.12, { type: 'sine', slide: -60, vol: 0.4 });
    this.noise(0.06, { freq: 2400, q: 2, vol: 0.08 });
  }
  good() {
    [660, 880, 1320].forEach((f, i) => this.tone(f, 0.18, { type: 'triangle', vol: 0.22, delay: i * 0.07 }));
  }
  soft() {
    this.tone(392, 0.16, { type: 'sine', vol: 0.25 });
    this.tone(330, 0.22, { type: 'sine', vol: 0.22, delay: 0.12 });
  }
  bump() {
    this.tone(110, 0.15, { type: 'sine', slide: -40, vol: 0.45 });
    this.noise(0.1, { freq: 700, q: 3, vol: 0.18 });
  }
  beep() {
    this.tone(1760, 0.09, { type: 'square', vol: 0.12 });
  }
  coin(k = 0) {
    const f = 1900 + k * 140;
    this.tone(f, 0.1, { type: 'sine', vol: 0.18 });
    this.tone(f * 1.5, 0.14, { type: 'sine', vol: 0.12, delay: 0.03 });
  }
  bill() {
    this.noise(0.14, { freq: 3000, q: 0.7, vol: 0.12 });
  }
  register() {
    this.tone(1318, 0.12, { type: 'triangle', vol: 0.25 });
    this.tone(1760, 0.3, { type: 'triangle', vol: 0.25, delay: 0.1 });
    this.noise(0.12, { freq: 4000, q: 1, vol: 0.12, delay: 0.1 });
  }
  win() {
    [523, 659, 784, 1046, 784, 1046].forEach((f, i) => this.tone(f, 0.22, { type: 'triangle', vol: 0.26, delay: i * 0.1 }));
  }
  click() {
    this.tone(880, 0.05, { type: 'triangle', vol: 0.12 });
  }
  whoosh() {
    this.noise(0.25, { freq: 900, q: 0.6, vol: 0.12 });
  }

  /** Volumen del traqueteo del carrito en función de la velocidad. */
  setRattle(speed) {
    if (!this.rattle) return;
    const v = this.sfxOn ? Math.min(0.09, speed * 0.022) : 0;
    this.rattle.g.gain.setTargetAtTime(v, this.ctx.currentTime, 0.08);
    this.rattle.bp.frequency.setTargetAtTime(600 + speed * 180, this.ctx.currentTime, 0.1);
  }

  /* música: arpegio tipo marimba con bajo, programada con anticipación */
  startMusic() {
    if (!this.ctx || this.musicTimer) return;
    const c = this.ctx;
    this.nextTime = c.currentTime + 0.1;
    const bpm = 104;
    const stepDur = 60 / bpm / 2;
    const chords = [
      [60, 64, 67, 72],
      [57, 60, 64, 69],
      [53, 57, 60, 65],
      [55, 59, 62, 67],
    ];
    const pattern = [0, 2, 1, 3, 2, 1, 3, 2];
    const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
    const play = (freq, t, dur, vol, type) => {
      const o = c.createOscillator();
      const g = c.createGain();
      o.type = type;
      o.frequency.value = freq;
      g.gain.setValueAtTime(0.0001, t);
      g.gain.exponentialRampToValueAtTime(vol, t + 0.01);
      g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      o.connect(g).connect(this.music);
      o.start(t);
      o.stop(t + dur + 0.05);
    };
    const tick = () => {
      while (this.nextTime < c.currentTime + 0.25) {
        const s = this.step;
        const bar = Math.floor(s / 8) % chords.length;
        const ch = chords[bar];
        const t = this.nextTime;
        if (this.musicOn) {
          const n = ch[pattern[s % 8]] + 12;
          if (s % 8 !== 7 || bar % 2) play(mtof(n), t, 0.32, 0.5, 'triangle');
          if (s % 4 === 0) play(mtof(ch[0] - 12), t, 0.5, 0.6, 'sine');
          if (s % 16 === 6) play(mtof(ch[2] + 24), t, 0.25, 0.18, 'sine');
        }
        this.step++;
        this.nextTime += stepDur;
      }
    };
    this.musicTimer = setInterval(tick, 90);
    tick();
  }
}
