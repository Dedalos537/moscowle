/*
 * Super RPG Bros. — motor.
 *
 * Plataformas 2D con física a 60 Hz fijos e interpolación de dibujo entre pasos (movimiento suave en pantallas de
 * 60/90/120 Hz). Inercia real al caminar/correr (aceleración que se suaviza cerca del tope, frenado progresivo,
 * derrape), gravedad distinta al subir/bajar, salto de altura variable con flotación en el punto alto, tiempo de
 * gracia al borde y salto anticipado. Colisión AABB contra la grilla de 16x16 y plataformas de un sentido.
 *
 * Dibujo: el mundo se ve con un zoom de 1,6 (personajes más grandes) y se pinta directo a la resolución del
 * dispositivo, con los mosaicos fijos pre-renderizados en una caché (con oclusión ambiental), sombras proyectadas
 * sobre el suelo, brillos aditivos pre-renderizados y cámara con anticipación y amortiguación vertical.
 * El marcador y los menús se dibujan aparte a 544x416.
 *
 * El juego no muestra KPIs: el marcador es el de cualquier plataformas (vidas, monedas, mundo, tiempo). Al salir,
 * envía las métricas de la partida a la plataforma con MoscowleGame (vendor/moscowle-bridge.js).
 */
(function () {
  'use strict';

  var A = window.SRBArt;
  var T = A.T;
  var W = 544; // resolución del marcador y de los menús
  var H = 416;
  var ZOOM = 1.6; // el mundo se ve 1,6 veces más grande
  var VW = W / ZOOM; // 340 px de mundo a lo ancho
  var VH = H / ZOOM; // 260 px de mundo a lo alto

  // ───────────────────────────── pantalla ─────────────────────────────
  var screen = document.getElementById('screen');
  var sctx = screen.getContext('2d');
  var buf = document.createElement('canvas');
  buf.width = W;
  buf.height = H;
  var g = buf.getContext('2d');
  g.imageSmoothingEnabled = false;
  var S = 1; // píxeles del lienzo por píxel de mundo

  function resize() {
    var box = screen.parentElement.getBoundingClientRect();
    var scale = Math.min(box.width / W, box.height / H);
    var cssW = Math.max(1, Math.floor(W * scale));
    var cssH = Math.max(1, Math.floor(H * scale));
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    // Tope de ~2,4 Mpx en el lienzo: tabletas modestas mantienen los 60 fps.
    if (cssW * cssH * dpr * dpr > 2400000) dpr = Math.sqrt(2400000 / (cssW * cssH));
    screen.style.width = cssW + 'px';
    screen.style.height = cssH + 'px';
    screen.width = Math.max(1, Math.round(cssW * dpr));
    screen.height = Math.max(1, Math.round(cssH * dpr));
    S = screen.width / VW;
    sctx.imageSmoothingEnabled = false;
  }
  window.addEventListener('resize', resize);

  // ───────────────────────────── fuente de mapa de bits 5x7 ─────────────────────────────
  var GLYPHS = {
    A: [14, 17, 17, 31, 17, 17, 17], B: [30, 17, 17, 30, 17, 17, 30], C: [14, 17, 16, 16, 16, 17, 14], D: [30, 17, 17, 17, 17, 17, 30],
    E: [31, 16, 16, 30, 16, 16, 31], F: [31, 16, 16, 30, 16, 16, 16], G: [14, 17, 16, 23, 17, 17, 15], H: [17, 17, 17, 31, 17, 17, 17],
    I: [14, 4, 4, 4, 4, 4, 14], J: [7, 2, 2, 2, 2, 18, 12], K: [17, 18, 20, 24, 20, 18, 17], L: [16, 16, 16, 16, 16, 16, 31],
    M: [17, 27, 21, 21, 17, 17, 17], N: [17, 17, 25, 21, 19, 17, 17], O: [14, 17, 17, 17, 17, 17, 14], P: [30, 17, 17, 30, 16, 16, 16],
    Q: [14, 17, 17, 17, 21, 18, 13], R: [30, 17, 17, 30, 20, 18, 17], S: [15, 16, 16, 14, 1, 1, 30], T: [31, 4, 4, 4, 4, 4, 4],
    U: [17, 17, 17, 17, 17, 17, 14], V: [17, 17, 17, 17, 17, 10, 4], W: [17, 17, 17, 21, 21, 21, 10], X: [17, 17, 10, 4, 10, 17, 17],
    Y: [17, 17, 10, 4, 4, 4, 4], Z: [31, 1, 2, 4, 8, 16, 31],
    0: [14, 17, 19, 21, 25, 17, 14], 1: [4, 12, 4, 4, 4, 4, 14], 2: [14, 17, 1, 2, 4, 8, 31], 3: [31, 2, 4, 2, 1, 17, 14],
    4: [2, 6, 10, 18, 31, 2, 2], 5: [31, 16, 30, 1, 1, 17, 14], 6: [6, 8, 16, 30, 17, 17, 14], 7: [31, 1, 2, 4, 8, 8, 8],
    8: [14, 17, 17, 14, 17, 17, 14], 9: [14, 17, 17, 15, 1, 2, 12],
    ' ': [0, 0, 0, 0, 0, 0, 0], '.': [0, 0, 0, 0, 0, 12, 12], ',': [0, 0, 0, 0, 12, 4, 8], ':': [0, 12, 12, 0, 12, 12, 0],
    '!': [4, 4, 4, 4, 4, 0, 4], '¡': [4, 0, 4, 4, 4, 4, 4], '?': [14, 17, 1, 2, 4, 0, 4], '¿': [4, 0, 4, 8, 16, 17, 14],
    '-': [0, 0, 0, 31, 0, 0, 0], '×': [0, 17, 10, 4, 10, 17, 0], '/': [1, 1, 2, 4, 8, 16, 16], "'": [4, 4, 8, 0, 0, 0, 0],
    Á: [2, 4, 14, 17, 31, 17, 17], É: [2, 4, 31, 16, 30, 16, 31], Í: [2, 4, 14, 4, 4, 4, 14], Ó: [2, 4, 14, 17, 17, 17, 14],
    Ú: [2, 4, 17, 17, 17, 17, 14], Ñ: [14, 0, 17, 25, 21, 19, 17], '(': [2, 4, 8, 8, 8, 4, 2], ')': [8, 4, 2, 2, 2, 4, 8],
    '+': [0, 4, 4, 31, 4, 4, 0], '·': [0, 0, 0, 12, 12, 0, 0], '>': [8, 4, 2, 1, 2, 4, 8], '<': [2, 4, 8, 16, 8, 4, 2],
  };

  function textWidth(str, s) {
    return str.length * 6 * (s || 1) - (s || 1);
  }

  function text(str, x, y, color, s, align, shadow) {
    s = s || 1;
    str = String(str).toUpperCase();
    if (align === 'center') x = Math.round(x - textWidth(str, s) / 2);
    else if (align === 'right') x = Math.round(x - textWidth(str, s));
    if (shadow) text(str, x + s, y + s, shadow, s);
    g.fillStyle = color || '#fff';
    for (var i = 0; i < str.length; i++) {
      var gl = GLYPHS[str[i]] || GLYPHS['?'];
      for (var r = 0; r < 7; r++) {
        var bits = gl[r];
        for (var c = 0; c < 5; c++) if (bits & (16 >> c)) g.fillRect(x + i * 6 * s + c * s, y + r * s, s, s);
      }
    }
  }

  // ───────────────────────────── entrada: teclado, mando y táctil ─────────────────────────────
  var keys = {};
  var pressed = {};
  var KEYMAP = {
    ArrowLeft: 'left', KeyA: 'left', ArrowRight: 'right', KeyD: 'right', ArrowUp: 'up', KeyW: 'up', ArrowDown: 'down', KeyS: 'down',
    KeyZ: 'a', Space: 'a', KeyK: 'a', KeyX: 'b', ShiftLeft: 'b', ShiftRight: 'b', KeyJ: 'b', Enter: 'start', Escape: 'pause', KeyP: 'pause',
  };
  function press(btn) {
    if (!keys[btn]) pressed[btn] = true;
    keys[btn] = true;
    Sound.unlock();
  }
  function release(btn) {
    keys[btn] = false;
  }
  window.addEventListener('keydown', function (e) {
    var b = KEYMAP[e.code];
    if (!b) return;
    e.preventDefault();
    press(b);
  });
  window.addEventListener('keyup', function (e) {
    var b = KEYMAP[e.code];
    if (b) release(b);
  });
  window.addEventListener('blur', function () {
    keys = {};
  });

  // Controles táctiles: cada botón de la capa HTML mantiene su estado con pointer events (multitáctil).
  Array.prototype.forEach.call(document.querySelectorAll('[data-btn]'), function (el) {
    var btn = el.getAttribute('data-btn');
    var on = function (e) {
      e.preventDefault();
      el.setPointerCapture && el.setPointerCapture(e.pointerId);
      el.classList.add('on');
      press(btn);
    };
    var off = function (e) {
      e.preventDefault();
      el.classList.remove('on');
      release(btn);
    };
    el.addEventListener('pointerdown', on);
    el.addEventListener('pointerup', off);
    el.addEventListener('pointercancel', off);
    el.addEventListener('lostpointercapture', off);
  });

  var padPrev = {};
  function pollGamepad() {
    var pads = navigator.getGamepads ? navigator.getGamepads() : [];
    var p = pads && pads[0];
    if (!p) return;
    var st = {
      left: p.axes[0] < -0.4 || (p.buttons[14] && p.buttons[14].pressed),
      right: p.axes[0] > 0.4 || (p.buttons[15] && p.buttons[15].pressed),
      up: p.axes[1] < -0.5 || (p.buttons[12] && p.buttons[12].pressed),
      down: p.axes[1] > 0.5 || (p.buttons[13] && p.buttons[13].pressed),
      a: p.buttons[0] && p.buttons[0].pressed,
      b: (p.buttons[2] && p.buttons[2].pressed) || (p.buttons[1] && p.buttons[1].pressed),
      start: p.buttons[9] && p.buttons[9].pressed,
    };
    for (var k in st) {
      if (st[k] && !padPrev[k]) press(k);
      if (!st[k] && padPrev[k]) release(k);
    }
    padPrev = st;
  }

  // Toques sobre el lienzo para los menús.
  var tap = null;
  screen.addEventListener('pointerdown', function (e) {
    var r = screen.getBoundingClientRect();
    tap = { x: ((e.clientX - r.left) / r.width) * W, y: ((e.clientY - r.top) / r.height) * H };
    Sound.unlock();
  });

  // ───────────────────────────── sonido (síntesis ligera, sin archivos) ─────────────────────────────
  var Sound = (function () {
    var ctx = null;
    var opts = { sfx: true, music: true };
    var musicTimer = null;
    var step = 0;
    function unlock() {
      if (!ctx) {
        try {
          ctx = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
          ctx = null;
        }
      }
      if (ctx && ctx.state === 'suspended') ctx.resume();
    }
    function tone(freq, dur, type, vol, slide, when) {
      if (!ctx) return;
      var t0 = ctx.currentTime + (when || 0);
      var o = ctx.createOscillator();
      var gn = ctx.createGain();
      o.type = type || 'square';
      o.frequency.setValueAtTime(freq, t0);
      if (slide) o.frequency.exponentialRampToValueAtTime(slide, t0 + dur);
      gn.gain.setValueAtTime(vol || 0.06, t0);
      gn.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      o.connect(gn).connect(ctx.destination);
      o.start(t0);
      o.stop(t0 + dur + 0.02);
    }
    var FX = {
      jump: function () { tone(330, 0.14, 'square', 0.05, 700); },
      coin: function () { tone(988, 0.07, 'square', 0.05); tone(1319, 0.22, 'square', 0.05, null, 0.07); },
      stomp: function () { tone(260, 0.12, 'triangle', 0.12, 90); },
      bump: function () { tone(120, 0.08, 'square', 0.06); },
      brick: function () { tone(180, 0.15, 'sawtooth', 0.05, 60); },
      power: function () { [523, 659, 784, 1046, 1318].forEach(function (f, i) { tone(f, 0.09, 'square', 0.05, null, i * 0.06); }); },
      appear: function () { [392, 523, 659].forEach(function (f, i) { tone(f, 0.08, 'triangle', 0.08, null, i * 0.05); }); },
      hurt: function () { tone(440, 0.3, 'square', 0.05, 110); },
      die: function () { [494, 466, 440, 392, 330, 262].forEach(function (f, i) { tone(f, 0.14, 'square', 0.05, null, i * 0.13); }); },
      fire: function () { tone(880, 0.06, 'sawtooth', 0.03, 300); },
      pipe: function () { [300, 220, 160].forEach(function (f, i) { tone(f, 0.1, 'square', 0.05, null, i * 0.1); }); },
      clear: function () { [523, 659, 784, 1046, 784, 1046, 1318].forEach(function (f, i) { tone(f, 0.15, 'square', 0.05, null, i * 0.12); }); },
      select: function () { tone(660, 0.05, 'square', 0.04); },
      oneup: function () { [659, 784, 1318, 1046, 1175, 1568].forEach(function (f, i) { tone(f, 0.08, 'square', 0.05, null, i * 0.08); }); },
      land: function () { tone(110, 0.07, 'triangle', 0.07, 60); },
      skid: function () { tone(520, 0.09, 'sawtooth', 0.018, 260); },
      swim: function () { tone(420, 0.09, 'sine', 0.06, 700); },
    };
    // Música: un bucle de 16 pasos con melodía y bajo, suave para no cansar.
    var MELODY = [659, 0, 784, 0, 880, 784, 659, 0, 587, 0, 659, 0, 523, 0, 0, 0];
    var BASS = [131, 0, 131, 0, 175, 0, 175, 0, 196, 0, 196, 0, 131, 0, 196, 0];
    function tick() {
      if (!ctx || !opts.music) return;
      var m = MELODY[step % 16];
      var b = BASS[step % 16];
      if (m) tone(m, 0.16, 'square', 0.018);
      if (b) tone(b, 0.2, 'triangle', 0.05);
      step++;
    }
    return {
      unlock: unlock,
      opts: opts,
      play: function (name) {
        if (opts.sfx && FX[name]) {
          unlock();
          FX[name]();
        }
      },
      music: function (on) {
        clearInterval(musicTimer);
        musicTimer = null;
        if (on && opts.music) musicTimer = setInterval(tick, 150);
      },
    };
  })();

  // ───────────────────────────── guardado y opciones ─────────────────────────────
  var SAVE_KEY = 'srb-save-v1';
  function loadSave() {
    try {
      return JSON.parse(localStorage.getItem(SAVE_KEY)) || null;
    } catch (e) {
      return null;
    }
  }
  function writeSave(s) {
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(s));
    } catch (e) {
      /* sin almacenamiento: el avance dura lo que la pestaña */
    }
  }
  var save = loadSave() || { unlocked: 1, cleared: [], options: { sfx: true, music: true, calm: false } };
  Sound.opts.sfx = save.options.sfx;
  Sound.opts.music = save.options.music;

  // ───────────────────────────── métricas de la partida (solo para el equipo) ─────────────────────────────
  var Stats = {
    attempts: 0, clears: 0, deaths: 0, stomps: 0, hits: 0, coins: 0, score: 0, clearTimes: [], best: 0,
    perLevel: {},
    level: function (id, available) {
      if (!this.perLevel[id]) this.perLevel[id] = { available: available, collected: 0 };
      return this.perLevel[id];
    },
    result: function () {
      var available = 0;
      var collected = 0;
      for (var k in this.perLevel) {
        available += this.perLevel[k].available;
        collected += this.perLevel[k].collected;
      }
      var touches = this.stomps + this.hits;
      return {
        game_name: 'Super RPG Bros.',
        accuracy: touches ? Math.round((this.stomps / touches) * 100) : this.attempts ? Math.round((this.clears / this.attempts) * 100) : 0,
        avg_time: this.clearTimes.length ? Math.round(this.clearTimes.reduce(function (a, b) { return a + b; }, 0) / this.clearTimes.length) : 0,
        level_reached: this.best,
        deaths: this.deaths,
        coins: this.coins,
        score: this.score,
        kpis: {
          completion: this.attempts ? Math.round((this.clears / this.attempts) * 100) : 0,
          errors: this.attempts ? Math.round((this.deaths / this.attempts) * 100) / 100 : 0,
          collected: available ? Math.round((collected / available) * 100) : 0,
        },
      };
    },
  };
  function report() {
    if (!window.MoscowleGame || Stats.attempts === 0) return Promise.resolve(false);
    return window.MoscowleGame.finish(Stats.result());
  }
  if (window.MoscowleGame) {
    window.MoscowleGame.start('Super RPG Bros.');
    window.MoscowleGame.onCollect && window.MoscowleGame.onCollect(function () { return Stats.attempts ? Stats.result() : null; });
  }
  window.addEventListener('pagehide', function () { report(); });

  // ───────────────────────────── mapa de tiles ─────────────────────────────
  var SOLID = { '#': 1, S: 1, B: 1, '?': 1, M: 1, U: 1, '[': 1, ']': 1, '{': 1, '}': 1 };
  function cell(map, tx, ty) {
    if (tx < 0 || tx >= map.w) return 'S';
    if (ty < 0) return map.vertical ? 'S' : ' ';
    if (ty >= map.h) return ' ';
    return map.grid[ty][tx];
  }
  function isSolid(ch) {
    return SOLID[ch] === 1;
  }
  function isWater(ch) {
    return ch === '~' || ch === 'w';
  }
  /** Cambia una celda y refresca la caché de dibujo (y las sombras proyectadas si cambió la solidez). */
  function setCell(map, tx, ty, ch) {
    var was = map.grid[ty][tx];
    map.grid[ty][tx] = ch;
    if (map.cache) for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) renderCell(map, tx + dx, ty + dy);
    if (isSolid(was) !== isSolid(ch)) buildCasters(map);
  }

  // ───────────────────────────── física ─────────────────────────────
  var PH = {
    walkMax: 1.6, runMax: 2.85, walkAcc: 0.075, runAcc: 0.1, airAcc: 0.068, airTurn: 0.11, skid: 0.22,
    fric: 0.055, fricK: 0.055, crouchFric: 0.06, airDrag: 0.008,
    jump: 5.3, jumpSpeedK: 0.22, gravHold: 0.17, holdFrames: 20, grav: 0.4, gravCut: 0.62, gravFall: 0.42,
    apexV: 0.9, apexK: 0.55, maxFall: 6.2, stomp: 4.6, stompHold: 6.2,
    waterGrav: 0.06, waterMaxFall: 1.2, swim: 2.2, waterMax: 1.3, waterAcc: 0.05, waterLeap: 4.6,
    enemyGrav: 0.36,
  };
  var COYOTE = 6;
  var BUFFER = 7;

  /** Mueve una caja contra la grilla: primero en X, luego en Y. Devuelve los contactos. */
  function move(e, map, opts) {
    opts = opts || {};
    var res = { wall: 0, ground: false, ceil: null };
    // Eje X
    e.x += e.vx;
    var top = Math.floor(e.y / T);
    var bottom = Math.floor((e.y + e.h - 0.01) / T);
    if (e.vx > 0) {
      var tx = Math.floor((e.x + e.w) / T);
      for (var ty = top; ty <= bottom; ty++) {
        if (isSolid(cell(map, tx, ty))) {
          e.x = tx * T - e.w;
          e.vx = 0;
          res.wall = 1;
          break;
        }
      }
    } else if (e.vx < 0) {
      var tx2 = Math.floor(e.x / T);
      for (var ty2 = top; ty2 <= bottom; ty2++) {
        if (isSolid(cell(map, tx2, ty2))) {
          e.x = (tx2 + 1) * T;
          e.vx = 0;
          res.wall = -1;
          break;
        }
      }
    }
    // Eje Y
    var prevBottom = e.y + e.h;
    e.y += e.vy;
    var left = Math.floor(e.x / T);
    var right = Math.floor((e.x + e.w - 0.01) / T);
    if (e.vy >= 0) {
      var by = Math.floor((e.y + e.h) / T);
      for (var x = left; x <= right; x++) {
        var ch = cell(map, x, by);
        var oneway = ch === '=' && prevBottom <= by * T + 0.5 && !opts.dropThrough;
        if (isSolid(ch) || oneway) {
          e.y = by * T - e.h;
          e.vy = 0;
          res.ground = true;
          break;
        }
      }
    } else {
      var ty3 = Math.floor(e.y / T);
      // El bloque que golpea la cabeza es el que está más cerca del centro.
      var cx = Math.floor((e.x + e.w / 2) / T);
      var order = [cx, left, right];
      for (var i = 0; i < order.length; i++) {
        var ch2 = cell(map, order[i], ty3);
        if (isSolid(ch2) || (opts.hidden && ch2 === 'H')) {
          e.y = (ty3 + 1) * T;
          e.vy = 0;
          res.ceil = { x: order[i], y: ty3 };
          break;
        }
      }
    }
    return res;
  }

  function overlap(a, b) {
    return a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;
  }

  /** Muelle de estirar/aplastar: sy vuelve a 1 con un pequeño rebote; sx compensa para conservar el volumen. */
  function spring(o) {
    o.sv = (o.sv + (1 - o.sy) * 0.3) * 0.62;
    o.sy += o.sv;
    if (Math.abs(o.sy - 1) < 0.003 && Math.abs(o.sv) < 0.003) {
      o.sy = 1;
      o.sv = 0;
    }
    o.sx = 1 + (1 - o.sy) * 0.85;
  }
  function squash(o, sy) {
    o.sy = sy;
    o.sv = 0;
    o.sx = 1 + (1 - sy) * 0.85;
  }

  // ───────────────────────────── estado del juego ─────────────────────────────
  var Game = {
    scene: 'title',
    lives: 3,
    coins: 0,
    score: 0,
    levelIndex: 0,
    menu: 0,
    frame: 0,
    timer: 0,
    sceneTime: 0,
    message: null,
  };

  var world = null; // nivel en juego
  var player = null;
  var entities = [];
  var particles = [];
  var bumps = [];
  var cam = { x: 0, y: 0, px: 0, py: 0, lead: 0, anchor: 0, shake: 0 };

  function setScene(name) {
    Game.scene = name;
    Game.sceneTime = 0;
    Game.menu = 0;
  }

  function newGame() {
    Game.lives = save.options.calm ? 7 : 5;
    Game.coins = 0;
    Game.score = 0;
    setScene('map');
    Game.levelIndex = Math.min(save.unlocked, window.SRBLevels.length) - 1;
  }

  function startLevel(index, fromCheckpoint, retry) {
    Game.levelIndex = index;
    var L = window.SRBLevels[index]();
    world = { main: L, current: L, startTime: Date.now(), checkpoint: fromCheckpoint || null, coinsHere: 0 };
    var lvStats = Stats.level(L.id, L.coinTotal());
    lvStats.available = L.coinTotal();
    // Reintentar tras perder una vida no es un intento nuevo: así «avance» y «errores» no se mezclan.
    if (!retry) Stats.attempts++;
    loadMap(L, fromCheckpoint || L.start);
    Game.timer = L.time && !save.options.calm ? L.time : null;
    setScene('intro');
  }

  function loadMap(map, at) {
    world.current = map;
    entities = [];
    particles = [];
    bumps = [];
    map.enemies.forEach(function (en) {
      entities.push(makeEnemy(en.type, en.x * T, en.y * T));
    });
    var keep = player ? { power: player.power } : { power: 0 };
    player = makePlayer(at.x * T + 2, at.y * T, keep.power);
    buildCache(map);
    buildCasters(map);
    snapCamera();
  }

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }
  function lerp(a, b, t) {
    return a + (b - a) * t;
  }

  // ───────────────────────────── jugador ─────────────────────────────
  function makePlayer(x, y, power) {
    var p = {
      kind: 'player', x: x, y: y, px: x, py: y, w: 12, h: power ? 30 : 15, vx: 0, vy: 0, face: 1, power: power || 0,
      onGround: false, coyote: 0, buffer: 0, holding: 0, crouch: false, invuln: 0, anim: 0, idleT: 0, state: 'idle',
      dead: false, deadT: 0, warp: null, goal: null, fireCool: 0, inWater: false, grow: 0, jumped: false,
      sx: 1, sy: 1, sv: 0, skid: false, stepT: 0, swimT: 0,
    };
    if (power) p.y -= 15;
    p.py = p.y;
    return p;
  }

  function setPower(p, power) {
    var was = p.power;
    p.power = power;
    var newH = power ? 30 : 15;
    if (p.crouch && power) newH = 15;
    p.y += p.h - newH;
    p.py = p.y;
    p.h = newH;
    if (power > was) p.grow = 40;
  }

  function hurtPlayer(p, from) {
    if (p.invuln > 0 || p.dead || p.goal) return;
    Stats.hits++;
    if (p.power > 0) {
      setPower(p, p.power === 2 ? 1 : 0);
      p.invuln = 100;
      // Retroceso suave: aleja a Ruy del golpe.
      var dir = from ? (p.x + p.w / 2 < from.x + from.w / 2 ? -1 : 1) : -p.face;
      p.vx = dir * 1.6;
      if (p.onGround) p.vy = -2.6;
      shake(2);
      Sound.play('hurt');
    } else {
      killPlayer(p);
    }
  }

  function killPlayer(p) {
    if (p.dead) return;
    p.dead = true;
    p.deadT = 0;
    p.vy = -6.2;
    p.vx = 0;
    Stats.deaths++;
    shake(3);
    Sound.music(false);
    Sound.play('die');
  }

  function updatePlayer(p) {
    var map = world.current;
    spring(p);
    if (p.dead) {
      p.deadT++;
      if (p.deadT > 30) {
        p.vy = Math.min(p.vy + 0.3, 6.5);
        p.y += p.vy;
      }
      if (p.deadT > 150) afterDeath();
      return;
    }
    if (p.warp) return updateWarp(p);
    if (p.goal) return updateGoal(p);

    var calm = save.options.calm ? 0.85 : 1;
    var feet = cell(map, Math.floor((p.x + p.w / 2) / T), Math.floor((p.y + p.h - 2) / T));
    var chest = cell(map, Math.floor((p.x + p.w / 2) / T), Math.floor((p.y + 4) / T));
    var wasWater = p.inWater;
    p.inWater = isWater(feet) || isWater(chest);
    if (p.inWater && !wasWater && p.vy > 1) {
      splash(p.x + p.w / 2, Math.floor((p.y + p.h) / T) * T, 6);
      p.vy *= 0.35;
    }

    var dir = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
    var run = keys.b;
    // Booleano estricto: `keys.down` es undefined hasta la primera pulsación (o tras perder el foco) y, sin esto,
    // Ruy grande «se ponía de pie» 15 px por cuadro y salía volando.
    var wantCrouch = !!(keys.down && p.onGround);
    if (wantCrouch !== p.crouch && p.power) {
      // Agacharse con Ruy grande reduce la caja; al pararse, solo si hay sitio.
      if (wantCrouch) {
        p.y += 15;
        p.py += 15;
        p.h = 15;
        p.crouch = true;
        squash(p, 0.8);
      } else if (!isSolid(cell(map, Math.floor(p.x / T), Math.floor((p.y - 15) / T))) && !isSolid(cell(map, Math.floor((p.x + p.w - 1) / T), Math.floor((p.y - 15) / T)))) {
        p.y -= 15;
        p.py -= 15;
        p.h = 30;
        p.crouch = false;
        squash(p, 1.12);
      }
    } else {
      p.crouch = wantCrouch;
    }
    if (p.crouch && p.onGround) dir = 0;

    // Horizontal con inercia: empuje fuerte al arrancar que se suaviza cerca del tope, frenado progresivo al
    // soltar, derrape al invertir el sentido y velocidad que se pierde poco a poco al dejar de correr.
    var max = (p.inWater ? PH.waterMax : run ? PH.runMax : PH.walkMax) * calm;
    var speed = Math.abs(p.vx);
    var wasSkid = p.skid;
    p.skid = false;
    if (dir !== 0) {
      p.face = dir;
      if (p.vx * dir < 0) {
        if (p.onGround && !p.inWater) {
          p.vx += dir * PH.skid;
          p.skid = speed > 1.0;
        } else {
          p.vx += dir * (p.inWater ? PH.waterAcc : PH.airTurn);
        }
      } else if (speed < max) {
        var a = p.inWater ? PH.waterAcc : p.onGround ? (run ? PH.runAcc : PH.walkAcc) : PH.airAcc;
        a *= 1.35 - 0.7 * (speed / max);
        p.vx += dir * a;
        if (Math.abs(p.vx) > max) p.vx = dir * max;
      } else {
        p.vx -= Math.sign(p.vx) * Math.min(speed - max, p.onGround ? 0.05 : 0.02);
      }
    } else {
      var dec = p.inWater ? 0.04 : p.onGround ? (p.crouch ? PH.crouchFric : PH.fric + speed * PH.fricK) : PH.airDrag;
      p.vx = speed <= dec ? 0 : p.vx - Math.sign(p.vx) * dec;
    }
    if (p.skid) {
      if (!wasSkid) Sound.play('skid');
      if (Game.frame % 3 === 0) dust(p.x + p.w / 2 + p.face * 4, p.y + p.h, 1, -p.face * 0.6);
    }

    // Salto: con tiempo de gracia al dejar el borde y pulsación anticipada antes de aterrizar.
    if (pressed.a) p.buffer = BUFFER;
    else if (p.buffer > 0) p.buffer--;
    if (p.onGround) p.coyote = COYOTE;
    else if (p.coyote > 0) p.coyote--;

    if (p.inWater) {
      if (pressed.a) {
        // Brazada; cerca de la superficie, un impulso extra saca a Ruy del agua.
        var above = cell(map, Math.floor((p.x + p.w / 2) / T), Math.floor((p.y - 6) / T));
        if (!isWater(above) && !isSolid(above)) p.vy = -PH.waterLeap;
        else p.vy = Math.max(-PH.swim * 1.15, Math.min(p.vy, 0) - PH.swim);
        p.swimT = 14;
        squash(p, 1.12);
        Sound.play('swim');
        bubbles(p.x + p.w / 2, p.y + 4, 3);
      }
      if (p.swimT > 0) p.swimT--;
      p.vy = Math.min(p.vy + PH.waterGrav, PH.waterMaxFall);
      if (Game.frame % 50 === 0) bubbles(p.x + p.w / 2 + p.face * 4, p.y + 2, 1);
    } else {
      if (p.buffer > 0 && p.coyote > 0) {
        p.vy = -(PH.jump + Math.abs(p.vx) * PH.jumpSpeedK) * (calm < 1 ? 0.98 : 1);
        p.buffer = 0;
        p.coyote = 0;
        p.holding = PH.holdFrames;
        p.onGround = false;
        p.jumped = true;
        squash(p, 1.3);
        Sound.play('jump');
        dust(p.x + p.w / 2, p.y + p.h, 3);
      }
      // Altura variable: mientras se mantiene A al subir, la gravedad es menor; al soltar, el salto se corta con
      // suavidad. En lo más alto, con A apretado, Ruy flota un instante.
      var grav;
      if (p.vy < 0) grav = keys.a ? (p.holding > 0 ? PH.gravHold : PH.grav) : PH.gravCut;
      else grav = PH.gravFall;
      if (keys.a && p.jumped && Math.abs(p.vy) < PH.apexV) grav *= PH.apexK;
      if (p.holding > 0) p.holding--;
      p.vy = Math.min(p.vy + grav, PH.maxFall);
    }

    // Disparo con la flor de fuego.
    if (p.fireCool > 0) p.fireCool--;
    if (pressed.b && p.power === 2 && p.fireCool === 0 && countFireballs() < 2) {
      entities.push(makeFireball(p.face > 0 ? p.x + p.w : p.x - 8, p.y + (p.crouch ? 4 : 8), p.face));
      p.fireCool = 14;
      squash(p, 0.92);
      Sound.play('fire');
    }

    var wasGround = p.onGround;
    var fallSpeed = p.vy;
    var res = move(p, map, { hidden: true, dropThrough: keys.down && keys.a });
    p.onGround = res.ground;
    if (res.ground && !wasGround) landed(p, fallSpeed);
    if (res.ceil) {
      squash(p, 0.86);
      hitBlock(res.ceil.x, res.ceil.y, p);
    }
    if (p.onGround) p.jumped = false;

    // Pasos: polvo suave al correr.
    if (p.onGround && speed > 1.9 && !p.skid) {
      p.stepT += speed;
      if (p.stepT > 26) {
        p.stepT = 0;
        dust(p.x + p.w / 2 - p.face * 4, p.y + p.h, 1, -p.face * 0.5);
      }
    }

    // Pinchos
    var px0 = Math.floor((p.x + 2) / T);
    var px1 = Math.floor((p.x + p.w - 2) / T);
    for (var tx = px0; tx <= px1; tx++) {
      if (cell(map, tx, Math.floor((p.y + p.h) / T)) === '^' && p.onGround) hurtPlayer(p);
    }

    // Monedas sueltas
    for (var cy = Math.floor(p.y / T); cy <= Math.floor((p.y + p.h - 1) / T); cy++) {
      for (var cx = px0 - 1; cx <= px1 + 1; cx++) {
        if (cell(map, cx, cy) === 'o' && overlap(p, { x: cx * T + 3, y: cy * T + 2, w: 10, h: 12 })) {
          setCell(map, cx, cy, ' ');
          addCoin(cx * T + 8, cy * T + 8, false);
        }
      }
    }

    // Tubería: de pie sobre una boca con atajo y pulsando abajo.
    if (p.onGround && keys.down) {
      var under = Math.floor((p.y + p.h + 1) / T);
      map.warps.forEach(function (wp) {
        if (!p.warp && wp.y === under && p.x >= wp.x * T + 2 && p.x + p.w <= (wp.x + 2) * T - 2) {
          p.warp = { t: 0, target: wp };
          Sound.play('pipe');
        }
      });
    }

    // Meta: solo al tocar el mástil o la bandera. En los niveles horizontales el mástil llega hasta el cielo (no se
    // puede saltar por encima); en la torre solo cuenta el tramo del mástil sobre la plataforma final.
    if (map.flagX !== null && map.flagX !== undefined && !p.goal && touchesPole(p, map)) {
      p.goal = { t: 0, phase: 'slide' };
      var poleX = map.flagX * T + 8;
      var fromRight = p.x + p.w / 2 > poleX;
      p.vx = 0;
      p.vy = 0;
      p.x = fromRight ? poleX + 2 : poleX - p.w - 2;
      p.face = fromRight ? -1 : 1;
      Sound.music(false);
      Sound.play('clear');
    }

    // Caída a un foso
    if (p.y > map.h * T + 24) killPlayer(p);

    if (p.invuln > 0) p.invuln--;
    if (p.grow > 0) p.grow--;

    // Animación
    if (p.onGround && !p.crouch && speed < 0.15 && dir === 0) p.idleT++;
    else p.idleT = 0;
    if (p.inWater && !p.onGround) p.state = 'swim';
    else if (!p.onGround) p.state = p.vy < -0.6 ? 'jump' : 'fall';
    else if (p.crouch) p.state = 'crouch';
    else if (p.skid) p.state = 'skid';
    else p.state = Math.abs(p.vx) > 0.15 ? 'run' : 'idle';
    p.anim += Math.abs(p.vx) * 0.105 + (Math.abs(p.vx) > 0.15 ? 0.04 : 0);

    // Punto de control a mitad del nivel (en la torre, a media altura), siempre sobre suelo firme.
    if (!world.checkpoint && map === world.main && p.onGround) {
      var half = map.vertical ? p.y + p.h < (map.h * T) / 2 : p.x > (map.w * T) / 2;
      if (half) world.checkpoint = { x: Math.floor(p.x / T), y: Math.floor((p.y + p.h) / T) - 2 };
    }
  }

  function touchesPole(p, map) {
    var x0 = map.flagX * T + 4;
    var top = map.vertical ? map.flagTop * T - 10 : -1e9;
    var bottom = (map.flagTop + 10) * T;
    return p.x + p.w > x0 && p.x < x0 + 8 && p.y + p.h > top && p.y < bottom;
  }

  function landed(p, impact) {
    if (impact > 1.2) squash(p, 1 - Math.min(0.34, impact * 0.055));
    if (impact > 2.5) dust(p.x + p.w / 2, p.y + p.h, Math.min(8, Math.round(impact * 1.2)));
    if (impact > 3.8) Sound.play('land');
    if (impact > 6) shake(1.6);
  }

  function countFireballs() {
    return entities.filter(function (e) { return e.kind === 'fireball'; }).length;
  }

  function updateWarp(p) {
    p.warp.t++;
    p.y += 0.8;
    if (p.warp.t === 40) {
      var wp = p.warp.target;
      var dest = wp.to === 'main' ? world.main : world.main.rooms[wp.to];
      var power = p.power;
      loadMap(dest, { x: wp.tx, y: wp.ty });
      player.power = power;
      setPower(player, power);
      player.grow = 0;
      Sound.play('pipe');
    }
  }

  function updateGoal(p) {
    var map = world.current;
    var gl = p.goal;
    gl.t++;
    if (gl.phase === 'slide') {
      var groundY = (map.flagTop + 10) * T - p.h;
      p.y = Math.min(groundY, p.y + 2.5);
      p.state = 'fall';
      if (gl.t % 4 === 0 && p.y < groundY) sparks(map.flagX * T + 8, p.y + p.h / 2, 1, '#fff6c2');
      if (p.y >= groundY && gl.t > 20) {
        gl.phase = 'walk';
        p.face = 1;
        landed(p, 3);
      }
    } else if (gl.phase === 'walk') {
      p.vx += (1.3 - p.vx) * 0.1;
      p.vy = Math.min(p.vy + PH.gravFall, PH.maxFall);
      var res = move(p, map);
      p.onGround = res.ground;
      p.state = 'run';
      p.anim += 0.18;
      if (gl.t > 110 || res.wall) {
        gl.phase = 'done';
        levelCleared();
      }
    }
  }

  function afterDeath() {
    Game.lives--;
    if (Game.lives <= 0) {
      setScene('gameover');
      player = null;
      return;
    }
    var cp = world.checkpoint;
    player = null;
    startLevel(Game.levelIndex, cp, true);
  }

  function levelCleared() {
    var L = world.main;
    var secs = Math.round((Date.now() - world.startTime) / 1000);
    Stats.clears++;
    Stats.clearTimes.push(secs);
    Stats.best = Math.max(Stats.best, Game.levelIndex + 1);
    var bonus = Game.timer ? Math.round(Game.timer) * 10 : 500;
    Game.score += bonus;
    Stats.score = Game.score;
    Game.message = { title: '¡NIVEL SUPERADO!', lines: ['MONEDAS ' + world.coinsHere + ' / ' + L.coinTotal(), 'TIEMPO ' + secs + 'S', 'BONO +' + bonus] };
    if (save.cleared.indexOf(L.id) < 0) save.cleared.push(L.id);
    save.unlocked = Math.max(save.unlocked, Math.min(window.SRBLevels.length, Game.levelIndex + 2));
    writeSave(save);
    setScene('clear');
  }

  // ───────────────────────────── bloques, monedas, partículas ─────────────────────────────
  function hitBlock(tx, ty, p) {
    var map = world.current;
    var ch = cell(map, tx, ty);
    if (ty < 0 || ty >= map.h || tx < 0 || tx >= map.w) return;
    bumps.push({ x: tx, y: ty, t: 0 });
    renderCell(map, tx, ty);
    // Un golpe desde abajo también derriba a los enemigos que estén encima y hace saltar a los objetos.
    entities.forEach(function (e) {
      var zone = { x: tx * T, y: ty * T - 4, w: T, h: 4 };
      if (e.enemy && !e.dead && overlap(e, zone)) defeatEnemy(e, 'bump', tx * T + 8);
      if (e.item && !e.rise && overlap(e, zone)) {
        e.vy = -3.6;
        if (e.kind === 'mushroom') e.vx = (e.x + e.w / 2 < tx * T + 8 ? -1 : 1) * 0.9;
      }
    });
    if (ch === '?' || ch === 'H') {
      setCell(map, tx, ty, 'U');
      addCoin(tx * T + 8, ty * T - 8, true);
    } else if (ch === 'M') {
      setCell(map, tx, ty, 'U');
      entities.push(makeItem(p.power ? 'flower' : 'mushroom', tx * T, ty * T));
      Sound.play('appear');
      sparks(tx * T + 8, ty * T, 6, '#fff6c2');
    } else if (ch === 'B') {
      if (p.power) {
        setCell(map, tx, ty, ' ');
        bumps = bumps.filter(function (b) { return !(b.x === tx && b.y === ty); });
        for (var i = 0; i < 6; i++) {
          var side = i % 2 ? 1 : -1;
          spawn({ kind: 'debris', x: tx * T + 8 + side * 3, y: ty * T + 4 + (i >> 1) * 3, vx: side * (0.8 + Math.random() * 1.2), vy: -3.6 - Math.random() * 1.8 + (i >> 1) * 0.6, grav: 0.32, life: 70, rot: Math.random() * 6, vr: side * (0.15 + Math.random() * 0.2) });
        }
        dust(tx * T + 8, ty * T + 12, 4);
        shake(1.5);
        Game.score += 50;
        Sound.play('brick');
      } else {
        Sound.play('bump');
      }
    } else {
      Sound.play('bump');
    }
  }

  function addCoin(x, y, popped) {
    Game.coins++;
    Game.score += 100;
    Stats.coins++;
    world.coinsHere++;
    var lv = Stats.level(world.main.id, world.main.coinTotal());
    lv.collected = Math.max(lv.collected, world.coinsHere);
    if (Game.coins >= 100) {
      Game.coins -= 100;
      Game.lives++;
      Sound.play('oneup');
    } else {
      Sound.play('coin');
    }
    if (popped) spawn({ kind: 'coin', x: x, y: y, vx: 0, vy: -4.6, grav: 0.28, life: 30 });
    sparks(x, y, popped ? 4 : 6, '#fff3b0');
    popup('100', x, y - 6);
  }

  var MAX_PARTICLES = 260;
  function spawn(o) {
    if (particles.length >= MAX_PARTICLES) particles.shift();
    o.px = o.x;
    o.py = o.y;
    o.max = o.life;
    o.grav = o.grav || 0;
    o.drag = o.drag || 1;
    o.rot = o.rot || 0;
    o.vr = o.vr || 0;
    particles.push(o);
    return o;
  }
  function dust(x, y, n, push) {
    for (var i = 0; i < n; i++) {
      var side = n > 1 ? (i % 2 ? 1 : -1) : 0;
      spawn({ kind: 'dust', x: x + (Math.random() - 0.5) * 6, y: y - 2, vx: side * (0.5 + Math.random() * 0.9) + (push || 0) + (Math.random() - 0.5) * 0.3, vy: -0.25 - Math.random() * 0.5, drag: 0.9, grav: -0.005, life: 20 + Math.random() * 10, size: 4 + Math.random() * 3 });
    }
  }
  function sparks(x, y, n, color) {
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2 + Math.random() * 0.6;
      var v = 1 + Math.random() * 1.4;
      spawn({ kind: 'spark', x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 0.6, drag: 0.92, grav: 0.05, life: 18 + Math.random() * 12, color: color || '#fff6c2' });
    }
  }
  function bubbles(x, y, n) {
    for (var i = 0; i < n; i++) spawn({ kind: 'bubble', x: x + (Math.random() - 0.5) * 8, y: y, vx: (Math.random() - 0.5) * 0.3, vy: -0.6 - Math.random() * 0.5, drag: 0.98, grav: -0.01, life: 50 + Math.random() * 30 });
  }
  function splash(x, y, n) {
    for (var i = 0; i < n; i++) spawn({ kind: 'drop', x: x + (Math.random() - 0.5) * 10, y: y, vx: (Math.random() - 0.5) * 2.2, vy: -2 - Math.random() * 2.2, grav: 0.22, life: 30 });
    bubbles(x, y + 10, 3);
  }
  function popup(str, x, y) {
    spawn({ kind: 'text', str: str, x: x, y: y, vx: 0, vy: -0.9, drag: 0.94, life: 45 });
  }
  function shake(v) {
    cam.shake = Math.max(cam.shake, v);
  }

  // ───────────────────────────── enemigos y objetos ─────────────────────────────
  function makeEnemy(type, x, y) {
    var e = {
      kind: type, enemy: true, x: x + 1, y: y + 1, w: 14, h: 15, vx: -0.45, vy: 0, dir: -1, speed: 0.45, dead: false, deadT: 0,
      anim: Math.random() * 4, active: false, homeY: y, face: -1, sx: 1, sy: 1, sv: 0, rot: 0, vr: 0,
    };
    if (type === 'bee') {
      e.vx = 0;
      e.fly = true;
      e.h = 13;
    }
    if (type === 'hog') {
      e.vx = -0.4;
      e.speed = 0.4;
      e.spiky = true;
      e.h = 13;
      e.y += 2;
    }
    e.px = e.x;
    e.py = e.y;
    return e;
  }

  function makeItem(kind, x, y) {
    return { kind: kind, item: true, x: x + 1, y: y, px: x + 1, py: y, w: 14, h: 15, vx: 0, vy: 0, rise: 16, startY: y, sx: 1, sy: 1, sv: 0, anim: 0 };
  }

  function makeFireball(x, y, dir) {
    return { kind: 'fireball', x: x, y: y, px: x, py: y, w: 8, h: 8, vx: 3.4 * dir, vy: 1, life: 160, anim: 0 };
  }

  function defeatEnemy(e, how, fromX) {
    if (e.dead) return;
    e.dead = true;
    e.deadT = 0;
    e.how = how;
    Game.score += 100;
    Stats.score = Game.score;
    popup('100', e.x + e.w / 2, e.y - 4);
    if (how === 'stomp') {
      e.vx = 0;
      squash(e, 0.45);
      Stats.stomps++;
      Sound.play('stomp');
      dust(e.x + e.w / 2, e.y + e.h, 4);
    } else {
      // Sale despedido en arco, girando, lejos del golpe.
      var away = fromX === undefined ? 1 : e.x + e.w / 2 < fromX ? -1 : 1;
      e.vy = -4.2;
      e.vx = away * 1.3;
      e.vr = away * 0.22;
      sparks(e.x + e.w / 2, e.y + e.h / 2, 5, how === 'fire' ? '#ffb347' : '#ffffff');
      Sound.play('stomp');
    }
  }

  function updateEntity(e) {
    var map = world.current;
    if (e.sv !== undefined) spring(e);
    if (e.enemy) {
      if (!e.active) {
        if (e.x < cam.x + VW + 48 && e.x > cam.x - 64 && e.y > cam.y - 64 && e.y < cam.y + VH + 64) e.active = true;
        else return;
      }
      if (e.dead) {
        e.deadT++;
        if (e.how === 'stomp') {
          if (e.deadT === 24) for (var k = 0; k < 3; k++) spawn({ kind: 'dust', x: e.x + 3 + k * 4, y: e.y + e.h - 2, vx: (k - 1) * 0.5, vy: -0.6, drag: 0.9, life: 22, size: 6 });
          if (e.deadT > 28) e.gone = true;
        } else {
          e.vy += 0.3;
          e.y += e.vy;
          e.x += e.vx;
          e.rot += e.vr;
          if (e.deadT > 150 || e.y > cam.y + VH + 80) e.gone = true;
        }
        return;
      }
      e.anim += e.fly ? 0.1 : 0.06 + Math.abs(e.vx) * 0.05;
      if (e.fly) {
        // Abeja: flota y, si Ruy está cerca, lo persigue despacio (con inercia).
        var dx = player.x - e.x;
        var dy = player.y - e.y;
        if (Math.abs(dx) < 150 && Math.abs(dy) < 110 && !player.dead) {
          e.vx += Math.sign(dx) * 0.03;
          e.vy += Math.sign(dy) * 0.02;
        } else {
          e.vx *= 0.96;
          e.vy += (e.homeY - e.y) * 0.002;
        }
        e.vx = clamp(e.vx, -0.8, 0.8);
        e.vy = clamp(e.vy, -0.6, 0.6) + Math.sin(e.anim * 2) * 0.05;
        if (Math.abs(e.vx) > 0.05) e.face = e.vx > 0 ? 1 : -1;
        move(e, map);
      } else {
        var fall = e.vy;
        e.vy = Math.min(e.vy + PH.enemyGrav, PH.maxFall);
        // El erizo no se cae de su plataforma: frena y da la vuelta en el borde.
        if (e.spiky && e.onGround) {
          var ahead = Math.floor((e.dir > 0 ? e.x + e.w + 1 : e.x - 1) / T);
          var below = Math.floor((e.y + e.h + 2) / T);
          var c2 = cell(map, ahead, below);
          if (!isSolid(c2) && c2 !== '=') {
            e.dir = -e.dir;
            e.vx *= 0.2;
            squash(e, 1.12);
          }
        }
        e.vx += (e.dir * e.speed - e.vx) * 0.08;
        var res = move(e, map);
        if (res.ground && !e.onGround && fall > 2) squash(e, 0.72);
        e.onGround = res.ground;
        if (res.wall) {
          e.dir = -res.wall;
          e.vx = e.dir * 0.1;
          squash(e, 1.15);
        }
        // Los enemigos chocan entre sí y se dan la vuelta.
        for (var i = 0; i < entities.length; i++) {
          var o = entities[i];
          if (o !== e && o.enemy && !o.fly && !o.dead && o.active && overlap(e, o) && (o.x - e.x) * e.dir > 0) {
            e.dir = -e.dir;
            e.vx *= 0.3;
          }
        }
        e.face = e.dir;
        if (e.y > map.h * T + 32) e.gone = true;
      }
      // Choque con Ruy: desde arriba lo derrota (salvo el erizo); de frente, daña a Ruy.
      if (player && !player.dead && !player.warp && !player.goal && overlap(player, e)) {
        var fromAbove = player.vy > 0 && (player.py + player.h <= e.py + 6 || player.y + player.h - e.y < 9);
        if (fromAbove && !e.spiky) {
          defeatEnemy(e, 'stomp');
          player.y = Math.min(player.y, e.y - player.h + 2);
          player.vy = keys.a ? -PH.stompHold : -PH.stomp;
          player.holding = 10;
          player.jumped = true;
          squash(player, 1.22);
        } else {
          hurtPlayer(player, e);
        }
      }
      return;
    }

    if (e.item) {
      e.anim += 0.05;
      if (e.rise > 0) {
        e.rise--;
        e.y -= 1;
        if (e.rise === 0 && e.kind === 'mushroom') e.vx = 0.9;
        return;
      }
      if (e.kind === 'mushroom' || e.vy !== 0) {
        var vy0 = e.vy;
        e.vy = Math.min(e.vy + PH.enemyGrav, PH.maxFall);
        var r = move(e, map);
        if (r.ground && vy0 > 1.6) {
          e.vy = -vy0 * 0.38; // rebote al caer desde alto
          squash(e, 0.75);
        }
        if (r.wall) {
          e.vx = -r.wall * 0.9;
          squash(e, 1.15);
        }
      }
      if (player && !player.dead && overlap(player, e)) {
        e.gone = true;
        Game.score += 1000;
        popup('1000', e.x + e.w / 2, e.y - 4);
        if (e.kind === 'mushroom' || player.power === 0) setPower(player, 1);
        else setPower(player, 2);
        sparks(player.x + player.w / 2, player.y + player.h / 2, 10, e.kind === 'flower' ? '#ffb347' : '#ffffff');
        spawn({ kind: 'ring', x: player.x + player.w / 2, y: player.y + player.h / 2, vx: 0, vy: 0, life: 24, color: e.kind === 'flower' ? '#ffb347' : '#fff6c2' });
        Sound.play('power');
      }
      if (e.y > map.h * T + 32) e.gone = true;
      return;
    }

    if (e.kind === 'fireball') {
      e.anim += 0.25;
      e.vy = Math.min(e.vy + 0.32, 4);
      var fr = move(e, map);
      if (fr.ground) e.vy = -3;
      if (Game.frame % 2 === 0) spawn({ kind: 'spark', x: e.x + 4, y: e.y + 4, vx: -e.vx * 0.1 + (Math.random() - 0.5) * 0.4, vy: -0.3, drag: 0.9, life: 14, color: '#ff9a3a' });
      if (fr.wall || --e.life <= 0 || e.x < cam.x - 32 || e.x > cam.x + VW + 32) {
        e.gone = true;
        sparks(e.x + 4, e.y + 4, 5, '#ffb347');
        return;
      }
      entities.forEach(function (en) {
        if (en.enemy && !en.dead && en.active && overlap(e, en)) {
          defeatEnemy(en, 'fire', e.x + 4 - Math.sign(e.vx) * 8);
          e.gone = true;
        }
      });
    }
  }

  function updateParticles() {
    var map = world.current;
    for (var i = 0; i < particles.length; i++) {
      var pt = particles[i];
      pt.px = pt.x;
      pt.py = pt.y;
      pt.vx *= pt.drag;
      pt.vy = pt.vy * pt.drag + pt.grav;
      pt.x += pt.vx;
      pt.y += pt.vy;
      pt.rot += pt.vr;
      pt.life--;
      if (pt.kind === 'debris' && pt.vy > 0 && !pt.bounced && isSolid(cell(map, Math.floor(pt.x / T), Math.floor((pt.y + 3) / T)))) {
        pt.vy *= -0.4;
        pt.vx *= 0.6;
        pt.vr *= 0.5;
        pt.bounced = true;
      }
      if (pt.kind === 'bubble' && !isWater(cell(map, Math.floor(pt.x / T), Math.floor(pt.y / T)))) pt.life = 0;
    }
    particles = particles.filter(function (pt) { return pt.life > 0; });
  }

  // ───────────────────────────── cámara ─────────────────────────────
  // Horizontal: sigue a Ruy con anticipación hacia donde corre. Vertical: se ancla al suelo que pisa y solo
  // persigue los saltos si Ruy sale de la franja central; así no tiembla con cada salto.
  function camTarget() {
    var p = player;
    return p.x + p.w / 2 + cam.lead - VW / 2;
  }
  function snapCamera() {
    var map = world.current;
    cam.lead = 0;
    cam.anchor = player.y + player.h;
    cam.x = clamp(camTarget(), 0, Math.max(0, map.w * T - VW));
    cam.y = clamp(cam.anchor - VH * 0.66, 0, Math.max(0, map.h * T - VH));
    cam.px = cam.x;
    cam.py = cam.y;
    cam.shake = 0;
  }
  function updateCamera() {
    var map = world.current;
    var p = player;
    var maxX = Math.max(0, map.w * T - VW);
    var maxY = Math.max(0, map.h * T - VH);
    if (!p.dead) {
      var leadTarget = clamp(p.face * 10 + p.vx * 12, -42, 42);
      cam.lead += (leadTarget - cam.lead) * 0.035;
      cam.x += (camTarget() - cam.x) * 0.11;
      var sx = p.x - cam.x;
      if (sx < VW * 0.16) cam.x = p.x - VW * 0.16;
      if (sx + p.w > VW * 0.84) cam.x = p.x + p.w - VW * 0.84;
      var feet = p.y + p.h;
      if (p.onGround || p.inWater || p.goal || p.warp || feet > cam.anchor) cam.anchor = feet;
      var ty = cam.anchor - VH * 0.66;
      if (p.y < cam.y + VH * 0.18) ty = Math.min(ty, p.y - VH * 0.18);
      var k = feet > cam.anchor - 1 && !p.onGround ? 0.16 : 0.075;
      cam.y += (ty - cam.y) * k;
      if (p.y + p.h > cam.y + VH * 0.92) cam.y = p.y + p.h - VH * 0.92;
    }
    cam.x = clamp(cam.x, 0, maxX);
    cam.y = clamp(cam.y, 0, maxY);
    cam.shake *= 0.84;
    if (cam.shake < 0.05) cam.shake = 0;
  }

  // ───────────────────────────── bucle principal ─────────────────────────────
  var last = performance.now();
  var acc = 0;
  var STEP = 1000 / 60;
  var alpha = 1;
  var frozen = false; // solo para pruebas: detiene la simulación automática (SRBDebug.step la avanza)
  var perf = { upd: 0, ren: 0, n: 0, steps: 0 };

  function frame(now) {
    acc += Math.min(100, now - last);
    last = now;
    pollGamepad();
    var t0 = performance.now();
    if (frozen) acc = 0;
    while (acc >= STEP) {
      update();
      acc -= STEP;
      pressed = {};
      tap = null;
      perf.steps++;
    }
    var t1 = performance.now();
    alpha = Game.scene === 'play' && !frozen ? acc / STEP : 1;
    render();
    var t2 = performance.now();
    perf.upd += t1 - t0;
    perf.ren += t2 - t1;
    perf.n++;
    requestAnimationFrame(frame);
  }

  function update() {
    Game.frame++;
    Game.sceneTime++;
    var sc = Game.scene;
    if (sc === 'title') return updateMenu(titleItems(), function (id) {
      if (id === 'new') {
        save.unlocked = 1;
        save.cleared = [];
        writeSave(save);
        newGame();
      } else if (id === 'continue') newGame();
      else if (id === 'options') setScene('options');
      else if (id === 'exit') exitGame();
    });
    if (sc === 'options') return updateMenu(optionItems(), function (id) {
      if (id === 'back') return setScene('title');
      save.options[id] = !save.options[id];
      Sound.opts.sfx = save.options.sfx;
      Sound.opts.music = save.options.music;
      writeSave(save);
    });
    if (sc === 'map') return updateMap();
    if (sc === 'intro') {
      if (Game.sceneTime > 100 || (Game.sceneTime > 20 && (pressed.a || pressed.start || tap))) {
        setScene('play');
        Sound.music(true);
      }
      return;
    }
    if (sc === 'play') return updatePlay();
    if (sc === 'pause') return updateMenu(withBoxes('pause', [{ id: 'resume', label: 'CONTINUAR' }, { id: 'map', label: 'VOLVER AL MAPA' }]), function (id) {
      if (id === 'resume') {
        Game.scene = 'play';
        Sound.music(true);
      } else {
        setScene('map');
      }
    });
    if (sc === 'clear') {
      if (Game.sceneTime > 70 && (pressed.a || pressed.start || tap || Game.sceneTime > 330)) {
        if (Game.levelIndex >= window.SRBLevels.length - 1) setScene('ending');
        else {
          Game.levelIndex = Math.min(save.unlocked - 1, Game.levelIndex + 1);
          setScene('map');
        }
      }
      return;
    }
    if (sc === 'gameover') {
      if (Game.sceneTime < 180) return;
      return updateMenu(withBoxes('gameover', [{ id: 'retry', label: 'REINTENTAR' }, { id: 'map', label: 'MAPA DEL MUNDO' }]), function (id) {
        Game.lives = save.options.calm ? 7 : 5;
        if (id === 'retry') startLevel(Game.levelIndex);
        else setScene('map');
      });
    }
    if (sc === 'ending') {
      if (Game.sceneTime > 120 && (pressed.a || pressed.start || tap)) {
        report();
        setScene('title');
      }
    }
  }

  function snapshot() {
    player.px = player.x;
    player.py = player.y;
    for (var i = 0; i < entities.length; i++) {
      entities[i].px = entities[i].x;
      entities[i].py = entities[i].y;
    }
    cam.px = cam.x;
    cam.py = cam.y;
  }

  function updatePlay() {
    if (pressed.pause || pressed.start) {
      Game.scene = 'pause';
      Game.menu = 0;
      Sound.music(false);
      return;
    }
    snapshot();
    var map = world.current;
    updatePlayer(player);
    if (!player) return;
    if (world.current !== map) return; // cambió de sala: la cámara ya se colocó
    entities.forEach(updateEntity);
    entities = entities.filter(function (e) { return !e.gone; });
    updateParticles();
    bumps.forEach(function (b) {
      b.t++;
      if (b.t >= 10) renderCell(map, b.x, b.y);
    });
    bumps = bumps.filter(function (b) { return b.t < 10; });

    if (Game.timer !== null && !player.dead && !player.goal && !world.current.isRoom) {
      Game.timer -= 1 / 40;
      if (Game.timer <= 0) {
        Game.timer = 0;
        killPlayer(player);
      }
    }
    updateCamera();
  }

  function updateMenu(items, onSelect) {
    if (pressed.up) {
      Game.menu = (Game.menu + items.length - 1) % items.length;
      Sound.play('select');
    }
    if (pressed.down) {
      Game.menu = (Game.menu + 1) % items.length;
      Sound.play('select');
    }
    if (tap) {
      items.forEach(function (it, i) {
        if (it.box && tap.x >= it.box.x && tap.x <= it.box.x + it.box.w && tap.y >= it.box.y && tap.y <= it.box.y + it.box.h) {
          Game.menu = i;
          Sound.play('select');
          onSelect(it.id);
        }
      });
      return;
    }
    if (pressed.a || pressed.start) {
      Sound.play('select');
      onSelect(items[Game.menu].id);
    }
    if (pressed.pause && Game.scene === 'options') setScene('title');
  }

  var menuBoxes = {};
  function titleItems() {
    var items = [{ id: 'new', label: 'NUEVA PARTIDA' }];
    if (save.unlocked > 1 || save.cleared.length) items.push({ id: 'continue', label: 'CONTINUAR' });
    items.push({ id: 'options', label: 'OPCIONES' }, { id: 'exit', label: 'SALIR' });
    return withBoxes('title', items);
  }
  function optionItems() {
    return withBoxes('options', [
      { id: 'sfx', label: 'SONIDO: ' + (save.options.sfx ? 'SÍ' : 'NO') },
      { id: 'music', label: 'MÚSICA: ' + (save.options.music ? 'SÍ' : 'NO') },
      { id: 'calm', label: 'MODO TRANQUILO: ' + (save.options.calm ? 'SÍ' : 'NO') },
      { id: 'back', label: 'VOLVER' },
    ]);
  }
  function withBoxes(key, items) {
    var boxes = menuBoxes[key] || [];
    items.forEach(function (it, i) { it.box = boxes[i]; });
    return items;
  }

  function exitGame() {
    report().then(function () {
      if (window.MoscowleGame && window.MoscowleGame.embedded) window.MoscowleGame.exit();
      else Game.message = { title: 'PUEDES CERRAR ESTA PESTAÑA', lines: [] };
    });
  }

  // Mapa del mundo: puntos unidos por un camino; se avanza entre los desbloqueados.
  var LEVEL_NAMES = null;
  var MAP_NODES = [
    { x: 92, y: 300 }, { x: 214, y: 214 }, { x: 330, y: 290 }, { x: 452, y: 196 },
  ];
  function updateMap() {
    var max = Math.min(save.unlocked, MAP_NODES.length) - 1;
    if (pressed.right && Game.levelIndex < max) {
      Game.levelIndex++;
      Sound.play('select');
    }
    if (pressed.left && Game.levelIndex > 0) {
      Game.levelIndex--;
      Sound.play('select');
    }
    if (tap) {
      MAP_NODES.forEach(function (n, i) {
        if (i <= max && Math.hypot(tap.x - n.x, tap.y - n.y) < 26) {
          if (Game.levelIndex === i) startLevel(i);
          else Game.levelIndex = i;
        }
      });
      return;
    }
    if (pressed.a || pressed.start) startLevel(Game.levelIndex);
    if (pressed.pause || pressed.b) setScene('title');
  }

  // ───────────────────────────── caché de mosaicos ─────────────────────────────
  // Los mosaicos fijos (suelo, ladrillos, piedra, tuberías…) con su oclusión ambiental se pintan una vez en
  // canvases de 1024 px de ancho; cada cuadro solo se copia el trozo visible. Los animados (?, monedas, agua)
  // se dibujan aparte.
  var CHUNK = 1024;
  var CACHED = { '#': 1, S: 1, B: 1, U: 1, '=': 1, '^': 1, '[': 1, ']': 1, '{': 1, '}': 1 };

  function buildCache(map) {
    var chunks = [];
    for (var x = 0; x < map.w * T; x += CHUNK) {
      var c = document.createElement('canvas');
      c.width = Math.min(CHUNK, map.w * T - x);
      c.height = map.h * T;
      chunks.push({ x: x, c: c, g: c.getContext('2d') });
    }
    map.cache = { chunks: chunks };
    map.tiles = A.tiles(map.theme);
    for (var ty = 0; ty < map.h; ty++) for (var tx = 0; tx < map.w; tx++) renderCell(map, tx, ty);
  }

  function tileImage(map, ch, tx, ty) {
    var t = map.tiles;
    var v = (tx * 7 + ty * 13) % 2;
    switch (ch) {
      case '#': {
        var up = cell(map, tx, ty - 1);
        return isSolid(up) ? t.ground[v] : t.top[v];
      }
      case 'S': return t.stone;
      case 'B': return t.brick;
      case 'U': return t.used;
      case '=': return t.platform;
      case '^': return t.spikes;
      case '[': return t.pipeTL;
      case ']': return t.pipeTR;
      case '{': return t.pipeL;
      case '}': return t.pipeR;
      case '?': case 'M': return t.question[0];
    }
    return null;
  }

  function isBumped(tx, ty) {
    for (var i = 0; i < bumps.length; i++) if (bumps[i].x === tx && bumps[i].y === ty && bumps[i].t < 10) return true;
    return false;
  }

  function renderCell(map, tx, ty) {
    if (!map.cache || tx < 0 || ty < 0 || tx >= map.w || ty >= map.h) return;
    var ck = map.cache.chunks[Math.floor((tx * T) / CHUNK)];
    var cg = ck.g;
    var x = tx * T - ck.x;
    var y = ty * T;
    var t = map.tiles;
    cg.clearRect(x, y, T, T);
    var ch = map.grid[ty][tx];
    if (CACHED[ch] && !isBumped(tx, ty)) {
      cg.drawImage(tileImage(map, ch, tx, ty), x, y);
      if (ch === '#') {
        // Más oscuro cuanto más hondo: da volumen al terreno.
        var depth = 0;
        while (depth < 4 && cell(map, tx, ty - depth - 1) === '#') depth++;
        if (depth > 0) {
          cg.fillStyle = 'rgba(20,10,30,' + (depth * 0.055).toFixed(3) + ')';
          cg.fillRect(x, y, T, T);
        }
      }
    }
    if (ch === '=') cg.drawImage(t.aoPlank, x, y);
    if (!isSolid(ch)) {
      // Oclusión ambiental solo donde hay algo detrás que reciba la sombra: rincones a ras de suelo, pasillos
      // bajos y el interior de cuevas/salas (en cielo abierto no se oscurece nada).
      var up = cell(map, tx, ty - 1);
      var down = cell(map, tx, ty + 1);
      var enclosed = map.theme === 'cave' || map.isRoom || isSolid(down) || isSolid(cell(map, tx, ty + 2));
      if (isSolid(up) && ty > 0 && enclosed) cg.drawImage(t.aoTop, x, y);
      if (isSolid(down) || down === '=') {
        if (isSolid(cell(map, tx - 1, ty)) && tx > 0) cg.drawImage(t.aoLeft, x, y);
        if (isSolid(cell(map, tx + 1, ty)) && tx < map.w - 1) cg.drawImage(t.aoRight, x, y);
      }
      if (down === '#' && !isWater(ch) && ch !== '=') cg.drawImage(t.tuft, x, y + T - 5);
    }
  }

  /** Bloques flotantes que proyectan una sombra suave sobre el suelo de abajo (se recalcula al cambiar la solidez). */
  function buildCasters(map) {
    var list = [];
    for (var ty = 0; ty < map.h - 1; ty++) {
      for (var tx = 0; tx < map.w; tx++) {
        var ch = map.grid[ty][tx];
        if (!(isSolid(ch) || ch === '=') || ch === '#' || ch === '{' || ch === '}') continue;
        if (isSolid(map.grid[ty + 1][tx]) || map.grid[ty + 1][tx] === '=') continue;
        for (var d = 2; d < 9 && ty + d < map.h; d++) {
          var c2 = map.grid[ty + d][tx];
          if (isWater(c2)) break;
          if (isSolid(c2) || c2 === '=') {
            list.push({ x: tx * T + 8, y: (ty + d) * T, k: 1 - d / 9 });
            break;
          }
        }
      }
    }
    map.casters = list;
  }

  // ───────────────────────────── dibujo del mundo (resolución del dispositivo) ─────────────────────────────
  var rcx = 0;
  var rcy = 0;
  function DX(x) {
    return Math.round((x - rcx) * S);
  }
  function DY(y) {
    return Math.round((y - rcy) * S);
  }
  function drawW(img, x, y) {
    var dx = DX(x);
    var dy = DY(y);
    sctx.drawImage(img, dx, dy, DX(x + img.width) - dx, DY(y + img.height) - dy);
  }
  /** Sprite anclado abajo al centro, con escala (estirar/aplastar) y giro opcional. */
  function drawWS(img, cx, by, sx, sy, rot) {
    var w = img.width * (sx || 1);
    var h = img.height * (sy || 1);
    if (!rot) {
      var x0 = DX(cx - w / 2);
      var y0 = DY(by - h);
      sctx.drawImage(img, x0, y0, DX(cx + w / 2) - x0, DY(by) - y0);
      return;
    }
    sctx.save();
    sctx.translate((cx - rcx) * S, (by - h / 2 - rcy) * S);
    sctx.rotate(rot);
    sctx.drawImage(img, (-w / 2) * S, (-h / 2) * S, w * S, h * S);
    sctx.restore();
  }
  function rectW(x, y, w, h, color) {
    var dx = DX(x);
    var dy = DY(y);
    sctx.fillStyle = color;
    sctx.fillRect(dx, dy, DX(x + w) - dx, DY(y + h) - dy);
  }
  function glowW(img, x, y, r, a) {
    if (a <= 0) return;
    sctx.globalAlpha = Math.min(1, a);
    sctx.drawImage(img, (x - r - rcx) * S, (y - r - rcy) * S, r * 2 * S, r * 2 * S);
  }

  // Fondo (cielo, capas, nubes, rayos) a resolución de mundo: una sola copia escalada por cuadro en lugar de varias
  // pasadas a pantalla completa (clave para tabletas sin mucha GPU).
  var bgc = document.createElement('canvas');
  bgc.width = Math.ceil(VW) + 2;
  bgc.height = Math.ceil(VH) + 2;
  var bgx = bgc.getContext('2d');
  var skyCache = { key: '', grad: null };
  /**
   * Cielo y capas de paralaje. Sirve para el mundo (ctx = lienzo, escala S) y para los menús (ctx = g, ZOOM).
   * anchorY: altura del suelo en el mundo; las capas se apoyan en él y se hunden al subir la cámara.
   */
  function drawBackdrop(ctx, theme, scale, camX, camY, camMaxY, anchorY, vertical, outW, outH) {
    var b = A.backdrop(theme);
    var viewH = outH / scale;
    var prog = vertical && camMaxY > 0 ? 1 - camY / camMaxY : 0;
    var key = theme + ':' + outH + ':' + Math.round(prog * 50) + ':' + (ctx === sctx ? 1 : 0);
    if (skyCache.key !== key) {
      var gr = ctx.createLinearGradient(0, 0, 0, outH);
      gr.addColorStop(0, A.mix(b.sky[0], b.skyHigh, prog));
      gr.addColorStop(1, A.mix(b.sky[1], b.sky[0], prog * 0.6));
      skyCache = { key: key, grad: gr };
    }
    ctx.fillStyle = skyCache.grad;
    ctx.fillRect(0, 0, outW, outH);
    var t = Game.frame;
    if (b.sun) {
      ctx.globalCompositeOperation = 'lighter';
      ctx.imageSmoothingEnabled = true;
      var sr = 70 * scale;
      var sx = outW * 0.72;
      var sy = outH * (0.42 + prog * 0.25);
      ctx.globalAlpha = 0.55;
      ctx.drawImage(A.glow.warm, sx - sr, sy - sr, sr * 2, sr * 2);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
      ctx.fillStyle = '#fff2c4';
      ctx.beginPath();
      ctx.arc(sx, sy, 18 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.imageSmoothingEnabled = false;
    }
    if (b.clouds && !vertical) drawLayerRow(ctx, b.clouds.img, scale, camX * b.clouds.kx + t * b.clouds.drift, 8 + (camMaxY - camY) * b.clouds.ky * 0.4, outW);
    for (var i = 0; i < b.layers.length; i++) {
      var L = b.layers[i];
      var k = L.ky;
      var bottom = anchorY + 40 - (camY * k + camMaxY * (1 - k));
      if (vertical) bottom = anchorY + 40 - camMaxY + (camMaxY - camY) * k;
      var top = bottom - L.img.height;
      if (top > viewH) continue;
      drawLayerRow(ctx, L.img, scale, camX * L.kx, top, outW);
      if (bottom < viewH) {
        ctx.fillStyle = L.img.bottomColor || '#000000';
        ctx.fillRect(0, Math.round(bottom * scale), outW, outH);
      }
    }
    if (b.clouds && vertical) {
      // En la torre las nubes pasan de largo al subir.
      var span = 300;
      var off = ((camY * 0.35) % span + span) % span;
      for (var y = -span + off - 40; y < viewH; y += span) drawLayerRow(ctx, b.clouds.img, scale, camX * 0.2 + t * b.clouds.drift, y, outW);
    }
    if (b.ceiling) {
      drawLayerRow(ctx, b.ceiling, scale, camX * 0.3, -((camY * 0.3) % 1) - 4, outW);
    }
    if (b.rays) {
      ctx.globalCompositeOperation = 'lighter';
      ctx.imageSmoothingEnabled = true;
      ctx.globalAlpha = 0.11 + 0.03 * Math.sin(t * 0.01);
      ctx.drawImage(A.rays, -((camX * 0.05) % 40) * scale - 20 * scale, 0, outW + 40 * scale, outH);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
      ctx.imageSmoothingEnabled = false;
    }
  }
  function drawLayerRow(ctx, img, scale, offX, topY, outW) {
    var lw = img.width;
    var ox = -(((offX % lw) + lw) % lw);
    var y0 = Math.round(topY * scale);
    var hh = Math.round((topY + img.height) * scale) - y0;
    for (var x = ox; x * scale < outW; x += lw) {
      var x0 = Math.round(x * scale);
      ctx.drawImage(img, x0, y0, Math.round((x + lw) * scale) - x0, hh);
    }
  }

  function drawCache(map) {
    var y0 = Math.max(0, Math.floor(rcy));
    var y1 = Math.min(map.h * T, Math.ceil(rcy + VH) + 1);
    if (y1 <= y0) return;
    map.cache.chunks.forEach(function (ck) {
      var x0 = Math.max(ck.x, Math.floor(rcx));
      var x1 = Math.min(ck.x + ck.c.width, Math.ceil(rcx + VW) + 1);
      if (x1 <= x0) return;
      var dx = DX(x0);
      var dy = DY(y0);
      sctx.drawImage(ck.c, x0 - ck.x, y0, x1 - x0, y1 - y0, dx, dy, DX(x1) - dx, DY(y1) - dy);
    });
  }

  function visibleCells(map) {
    return {
      x0: Math.max(0, Math.floor(rcx / T)),
      x1: Math.min(map.w - 1, Math.floor((rcx + VW) / T)),
      y0: Math.max(0, Math.floor(rcy / T)),
      y1: Math.min(map.h - 1, Math.floor((rcy + VH) / T)),
    };
  }

  /** Mosaicos animados: bloques «?», monedas y bloques que rebotan. Primero los brillos, luego los sprites. */
  function drawDynamicTiles(map) {
    var v = visibleCells(map);
    var t = map.tiles;
    var f = Game.frame;
    var qf = [0, 0, 0, 0, 1, 2, 3, 0][Math.floor(f / 7) % 8];
    var cf = Math.floor(f / 6) % 6;
    var list = [];
    for (var ty = v.y0; ty <= v.y1; ty++) {
      for (var tx = v.x0; tx <= v.x1; tx++) {
        var ch = map.grid[ty][tx];
        if (ch === '?' || ch === 'M' || ch === 'o' || (CACHED[ch] && bumps.length && isBumped(tx, ty))) list.push(tx, ty);
      }
    }
    if (!list.length) return;
    sctx.globalCompositeOperation = 'lighter';
    sctx.imageSmoothingEnabled = true;
    for (var i = 0; i < list.length; i += 2) {
      var c = map.grid[list[i + 1]][list[i]];
      var gx = list[i] * T + 8;
      var gy = list[i + 1] * T + 8;
      if (c === 'o') glowW(A.glow.warm, gx, gy, 13, 0.32 + 0.08 * Math.sin(f * 0.08 + list[i]));
      else if (c === '?' || c === 'M') glowW(A.glow.warm, gx, gy, 22, 0.16 + 0.06 * Math.sin(f * 0.06 + list[i] * 0.7));
    }
    sctx.globalAlpha = 1;
    sctx.globalCompositeOperation = 'source-over';
    sctx.imageSmoothingEnabled = false;
    for (var j = 0; j < list.length; j += 2) {
      var tx2 = list[j];
      var ty2 = list[j + 1];
      var ch2 = map.grid[ty2][tx2];
      var off = 0;
      for (var b = 0; b < bumps.length; b++) if (bumps[b].x === tx2 && bumps[b].y === ty2) off = Math.sin((bumps[b].t / 10) * Math.PI) * 5;
      if (ch2 === 'o') {
        var img = A.coin[(cf + tx2) % 6];
        drawW(img, tx2 * T + 8 - img.width / 2, ty2 * T + 1 + Math.sin(f * 0.07 + tx2 * 0.8) * 1.2);
      } else if (ch2 === '?' || ch2 === 'M') {
        drawW(t.question[qf], tx2 * T, ty2 * T - off);
      } else {
        drawW(tileImage(map, ch2, tx2, ty2), tx2 * T, ty2 * T - off);
      }
    }
  }

  function drawWater(map) {
    var v = visibleCells(map);
    var t = map.tiles;
    var f = Math.floor(Game.frame / 9) % 4;
    for (var ty = v.y0; ty <= v.y1; ty++) {
      for (var tx = v.x0; tx <= v.x1; tx++) {
        var ch = map.grid[ty][tx];
        if (ch === '~') drawW(t.water[(f + tx) % 4], tx * T, ty * T);
        else if (ch === 'w') drawW(t.waterDeep[(f + (tx >> 1)) % 4], tx * T, ty * T);
      }
    }
  }

  function groundBelow(map, x0, x1, footY) {
    var ty = Math.floor((footY - 1) / T);
    for (var d = 0; d < 9; d++) {
      var row = ty + d;
      if (row >= map.h) return null;
      for (var tx = Math.floor(x0 / T); tx <= Math.floor((x1 - 1) / T); tx++) {
        var ch = cell(map, tx, row);
        if (isWater(ch)) return null;
        if ((isSolid(ch) || ch === '=') && row * T >= footY - 1) return row * T;
      }
    }
    return null;
  }

  function shadowFor(map, x, y, w, h, strength) {
    var top = groundBelow(map, x + 2, x + w - 2, y + h);
    if (top === null) return;
    var dist = top - (y + h);
    var k = 1 - dist / (9 * T);
    if (k <= 0) return;
    var sw = (w + 8) * (0.55 + 0.45 * k);
    var sh = sw * 0.26;
    sctx.globalAlpha = 0.42 * k * (strength || 1);
    var x0 = DX(x + w / 2 - sw / 2);
    var y0 = DY(top - sh / 2 + 1);
    sctx.drawImage(A.shadow, x0, y0, DX(x + w / 2 + sw / 2) - x0, Math.max(1, DY(top + sh / 2 + 1) - y0));
  }

  function drawShadows(map) {
    sctx.imageSmoothingEnabled = true;
    var cs = map.casters;
    for (var i = 0; i < cs.length; i++) {
      var c = cs[i];
      if (c.x < rcx - 16 || c.x > rcx + VW + 16 || c.y < rcy - 8 || c.y > rcy + VH + 8) continue;
      sctx.globalAlpha = 0.3 * c.k;
      var x0 = DX(c.x - 11);
      var y0 = DY(c.y - 2);
      sctx.drawImage(A.shadow, x0, y0, DX(c.x + 11) - x0, Math.max(1, DY(c.y + 4) - y0));
    }
    entities.forEach(function (e) {
      if (e.dead || (e.item && e.rise > 0)) return;
      var ix = lerp(e.px, e.x, alpha);
      var iy = lerp(e.py, e.y, alpha);
      if (ix < rcx - 32 || ix > rcx + VW + 32) return;
      shadowFor(map, ix, iy, e.w, e.h, e.kind === 'fireball' ? 0.6 : 1);
    });
    var p = player;
    if (p && !p.dead && !p.warp) shadowFor(map, lerp(p.px, p.x, alpha), lerp(p.py, p.y, alpha), p.w, p.h, 1);
    sctx.globalAlpha = 1;
    sctx.imageSmoothingEnabled = false;
  }

  function drawFlag(map) {
    if (map.flagX === null || map.flagX === undefined) return;
    var x = map.flagX * T + 7;
    var top = map.flagTop * T;
    var bottom = (map.flagTop + 10) * T;
    if (top > rcy + VH + 20 || bottom < rcy - 20) return;
    rectW(x - 1, top, 4, bottom - top, '#1b1d2e');
    rectW(x, top, 2, bottom - top, '#d5dbea');
    rectW(x, top, 1, bottom - top, '#ffffff');
    rectW(x - 3, bottom - 4, 8, 4, '#1b1d2e');
    rectW(x - 2, bottom - 3, 6, 3, '#8f97b3');
    var flagY = top + 4;
    if (player && player.goal) flagY = Math.min(bottom - 24, lerp(player.py, player.y, alpha));
    drawW(A.flag[Math.floor(Game.frame / 8) % 3], x - 16, flagY);
    rectW(x - 3, top - 6, 8, 7, '#1b1d2e');
    rectW(x - 2, top - 5, 6, 5, '#ffd43a');
    rectW(x - 2, top - 5, 2, 2, '#fff4b0');
  }

  function playerFrame(p) {
    if (p.dead) return 'dead';
    if (p.goal && p.goal.phase === 'slide') return 'fall';
    switch (p.state) {
      case 'run': return 'run' + (Math.floor(p.anim) % 6);
      case 'jump': return 'jump';
      case 'fall': return 'fall';
      case 'skid': return 'skid';
      case 'crouch': return 'crouch';
      case 'swim': return p.swimT > 6 ? 'swim1' : 'swim0';
    }
    if (p.idleT % 200 > 192) return 'blink';
    return Math.floor(p.idleT / 36) % 2 ? 'breath' : 'idle';
  }

  function drawPlayer(p) {
    if (!p) return;
    if (p.invuln > 0 && Math.floor(p.invuln / 3) % 2 === 0) return;
    var set = p.power === 2 ? A.ruyFire : A.ruy;
    var big = p.power > 0 && !(p.grow > 0 && Math.floor(p.grow / 4) % 2 === 0);
    var frames = big ? set.big : set.small;
    var spr = frames[playerFrame(p)] || frames.idle;
    var img = p.face < 0 ? spr.l : spr.r;
    var ix = lerp(p.px, p.x, alpha);
    var iy = lerp(p.py, p.y, alpha);
    var cx = ix + p.w / 2 + p.face * 0.5;
    var by = iy + p.h + 1;
    if (p.warp) {
      sctx.save();
      sctx.beginPath();
      sctx.rect(0, 0, screen.width, DY(p.warp.target.y * T));
      sctx.clip();
      drawWS(img, cx, by, 1, 1);
      sctx.restore();
      return;
    }
    drawWS(img, cx, by, p.sx, p.sy);
  }

  function drawEntity(e) {
    var ix = lerp(e.px, e.x, alpha);
    var iy = lerp(e.py, e.y, alpha);
    if (ix < rcx - 40 || ix > rcx + VW + 40 || iy < rcy - 40 || iy > rcy + VH + 40) return;
    var cx = ix + e.w / 2;
    var by = iy + e.h + 1;
    var face = e.face > 0 ? 'r' : 'l';
    if (e.enemy) {
      var rot = e.dead && e.how !== 'stomp' ? Math.PI + e.rot : 0;
      if (e.kind === 'blob') {
        if (e.dead && e.how === 'stomp') {
          sctx.globalAlpha = e.deadT > 18 ? Math.max(0, 1 - (e.deadT - 18) / 10) : 1;
          drawWS(A.blobFlat[face], cx, by, e.sx, Math.max(0.6, e.sy));
          sctx.globalAlpha = 1;
        } else drawWS(A.blob[Math.floor(e.anim * 2.4) % 4][face], cx, by, e.sx, e.sy, rot);
      } else if (e.kind === 'bee') {
        drawWS(A.bee[Math.floor(Game.frame / 2) % 4][face], cx, by + 2 + Math.sin(e.anim * 3) * 0.8, e.sx, e.sy, rot);
      } else if (e.kind === 'hog') {
        drawWS(A.hog[Math.floor(e.anim * 2.2) % 4][face], cx, by, e.sx, e.sy, rot);
      }
      return;
    }
    if (e.item) {
      var clipY = e.rise > 0 ? DY(e.startY) : null;
      if (clipY !== null) {
        sctx.save();
        sctx.beginPath();
        sctx.rect(0, 0, screen.width, clipY);
        sctx.clip();
      }
      if (e.kind === 'mushroom') drawWS(A.mushroom, cx, by, e.sx, e.sy);
      else drawWS(A.flower[Math.floor(e.anim * 2) % 4], cx, by + 1, e.sx, e.sy);
      if (clipY !== null) sctx.restore();
      return;
    }
    if (e.kind === 'fireball') drawWS(A.fireball[Math.floor(e.anim) % 4], cx, by + 1, 1, 1);
  }

  function drawDeco(map) {
    map.deco.forEach(function (d) {
      var img = d.kind === 'bush' ? A.bush : A.fence;
      var x = d.x * T;
      var y = d.y * T - img.height + (d.kind === 'bush' ? 3 : 1);
      if (x > rcx - 40 && x < rcx + VW + 8 && y < rcy + VH + 8 && y + img.height > rcy) drawW(img, x, y);
    });
  }

  function drawParticles(map) {
    var tiles = map.tiles;
    for (var i = 0; i < particles.length; i++) {
      var pt = particles[i];
      var x = lerp(pt.px, pt.x, alpha);
      var y = lerp(pt.py, pt.y, alpha);
      if (x < rcx - 20 || x > rcx + VW + 20 || y < rcy - 20 || y > rcy + VH + 20) continue;
      var k = pt.life / pt.max;
      switch (pt.kind) {
        case 'dust': {
          var s = pt.size * (1.5 - k * 0.6);
          sctx.globalAlpha = Math.min(1, k * 1.3) * 0.85;
          var x0 = DX(x - s / 2);
          var y0 = DY(y - s / 2);
          sctx.drawImage(A.puff, x0, y0, Math.max(1, DX(x + s / 2) - x0), Math.max(1, DY(y + s / 2) - y0));
          sctx.globalAlpha = 1;
          break;
        }
        case 'debris':
          sctx.globalAlpha = Math.min(1, k * 3);
          drawWS(tiles.debris, x, y + 3, 1, 1, pt.rot);
          sctx.globalAlpha = 1;
          break;
        case 'coin': {
          var img = A.coin[Math.floor(pt.life / 2) % 6];
          drawW(img, x - img.width / 2, y - 8);
          break;
        }
        case 'bubble':
          drawW(A.bubble, x - 2, y - 2);
          break;
        case 'drop':
          rectW(x, y, 1.5, 2, 'rgba(210,240,255,0.9)');
          break;
        case 'ring': {
          var r = (1 - k) * 26 + 6;
          sctx.globalAlpha = k;
          sctx.strokeStyle = pt.color;
          sctx.lineWidth = Math.max(1, 2 * S * k);
          sctx.beginPath();
          sctx.arc((x - rcx) * S, (y - rcy) * S, r * S, 0, Math.PI * 2);
          sctx.stroke();
          sctx.globalAlpha = 1;
          break;
        }
      }
    }
  }

  /** Brillos aditivos: chispas, bolas de fuego, flor de fuego, champiñón y el aura de Ruy al crecer o tras un golpe. */
  function drawGlows() {
    sctx.globalCompositeOperation = 'lighter';
    sctx.imageSmoothingEnabled = true;
    var f = Game.frame;
    entities.forEach(function (e) {
      var ix = lerp(e.px, e.x, alpha) + e.w / 2;
      var iy = lerp(e.py, e.y, alpha) + e.h / 2;
      if (ix < rcx - 40 || ix > rcx + VW + 40) return;
      if (e.kind === 'fireball') glowW(A.glow.fire, ix, iy, 22, 0.75 + 0.15 * Math.sin(f * 0.5));
      else if (e.kind === 'flower') glowW(A.glow.fire, ix, iy - 3, 24, 0.35 + 0.12 * Math.sin(f * 0.1));
      else if (e.kind === 'mushroom') glowW(A.glow.white, ix, iy, 18, 0.18 + 0.06 * Math.sin(f * 0.1));
    });
    for (var i = 0; i < particles.length; i++) {
      var pt = particles[i];
      if (pt.kind !== 'spark') continue;
      var k = pt.life / pt.max;
      var x = lerp(pt.px, pt.x, alpha);
      var y = lerp(pt.py, pt.y, alpha);
      glowW(pt.color === '#ff9a3a' || pt.color === '#ffb347' ? A.glow.fire : A.glow.warm, x, y, 5 + 3 * k, k * 0.9);
      sctx.globalAlpha = k;
      sctx.imageSmoothingEnabled = false;
      var s = k > 0.5 ? 2 : 1;
      sctx.fillStyle = pt.color;
      sctx.fillRect(DX(x - s / 2), DY(y - s / 2), Math.max(1, Math.round(s * S)), Math.max(1, Math.round(s * S)));
      sctx.imageSmoothingEnabled = true;
    }
    var p = player;
    if (p && !p.dead && (p.grow > 0 || p.invuln > 0 || p.goal)) {
      var px = lerp(p.px, p.x, alpha) + p.w / 2;
      var py = lerp(p.py, p.y, alpha) + p.h / 2;
      glowW(A.glow.white, px, py, 26, p.grow > 0 ? 0.35 : 0.18);
      sctx.globalAlpha = 0.9;
      sctx.imageSmoothingEnabled = false;
      for (var s2 = 0; s2 < 3; s2++) {
        var a = f * 0.12 + s2 * 2.1;
        drawW(A.sparkle, px + Math.cos(a) * 12 - 3, py + Math.sin(a * 1.3) * 14 - 3);
      }
    }
    if (p && p.power === 2 && !p.dead) glowW(A.glow.fire, lerp(p.px, p.x, alpha) + p.w / 2, lerp(p.py, p.y, alpha) + p.h / 2, 20, 0.12);
    sctx.globalAlpha = 1;
    sctx.globalCompositeOperation = 'source-over';
    sctx.imageSmoothingEnabled = false;
  }

  function drawAtmosphere(map) {
    var b = A.backdrop(map.theme);
    var sw = screen.width;
    var sh = screen.height;
    sctx.imageSmoothingEnabled = true;
    if (b.dark && player) {
      // Cueva: la oscuridad se abre alrededor de Ruy.
      var px = (lerp(player.px, player.x, alpha) + player.w / 2 - rcx) * S;
      var py = (lerp(player.py, player.y, alpha) + player.h / 2 - rcy) * S;
      // Solo se copia el trozo que cae en pantalla (un dibujo enorme fuera de pantalla es caro sin GPU).
      var r = 440 * S;
      var k = A.darkness.width / (r * 2);
      var sx0 = Math.max(0, (0 - (px - r)) * k);
      var sy0 = Math.max(0, (0 - (py - r)) * k);
      var sx1 = Math.min(A.darkness.width, (sw - (px - r)) * k);
      var sy1 = Math.min(A.darkness.height, (sh - (py - r)) * k);
      if (sx1 > sx0 && sy1 > sy0) sctx.drawImage(A.darkness, sx0, sy0, sx1 - sx0, sy1 - sy0, px - r + sx0 / k, py - r + sy0 / k, (sx1 - sx0) / k, (sy1 - sy0) / k);
    }
    if (!b.dark || !player) {
      // En la cueva la oscuridad ya oscurece los bordes: no hace falta otra pasada de viñeta.
      sctx.globalAlpha = b.vignette || 0.25;
      sctx.drawImage(A.vignette, 0, 0, sw, sh);
    }
    sctx.globalAlpha = 1;
    sctx.imageSmoothingEnabled = false;
  }

  function renderWorld() {
    var map = world.current;
    var maxY = Math.max(0, map.h * T - VH);
    var shx = cam.shake ? Math.sin(Game.frame * 7.3) * cam.shake : 0;
    var shy = cam.shake ? Math.cos(Game.frame * 5.1) * cam.shake : 0;
    rcx = lerp(cam.px, cam.x, alpha) + shx;
    rcy = lerp(cam.py, cam.y, alpha) + shy;
    sctx.setTransform(1, 0, 0, 1, 0, 0);
    sctx.imageSmoothingEnabled = false;
    var anchorY = map.vertical ? (map.h - 4) * T : 22 * T;
    bgx.imageSmoothingEnabled = false;
    drawBackdrop(bgx, map.theme, 1, rcx, rcy, maxY, anchorY, map.vertical, bgc.width, bgc.height);
    sctx.drawImage(bgc, 0, 0, Math.round(bgc.width * S), Math.round(bgc.height * S));
    drawCache(map);
    drawShadows(map);
    drawDynamicTiles(map);
    drawFlag(map);
    entities.forEach(function (e) { if (!e.enemy || !e.dead || e.how === 'stomp') drawEntity(e); });
    drawPlayer(player);
    entities.forEach(function (e) { if (e.enemy && e.dead && e.how !== 'stomp') drawEntity(e); });
    drawParticles(map);
    drawWater(map);
    drawDeco(map);
    drawAtmosphere(map);
    drawGlows();
  }

  // ───────────────────────────── marcador y menús (544x416) ─────────────────────────────
  function drawHud() {
    g.fillStyle = 'rgba(10,12,30,0.5)';
    g.fillRect(0, 0, W, 34);
    g.fillStyle = 'rgba(255,255,255,0.1)';
    g.fillRect(0, 34, W, 1);
    var map = world.main;
    var face = (player && player.power === 2 ? A.ruyFire : A.ruy).small.idle.r;
    g.drawImage(face, 0, 0, 18, 13, 6, 5, 36, 26);
    text('×' + Game.lives, 46, 12, '#ffffff', 2, null, '#1b1d2e');
    var coin = A.coin[Math.floor(Game.frame / 8) % 6];
    g.drawImage(coin, 102 + Math.round((14 - coin.width) * 0.75), 5, Math.round(coin.width * 1.5), 24);
    text('×' + String(Game.coins).padStart(2, '0'), 126, 12, '#ffd43a', 2, null, '#1b1d2e');
    text('MUNDO', W / 2, 5, '#9fd3ff', 1, 'center', '#1b1d2e');
    text(map.id, W / 2, 15, '#ffffff', 2, 'center', '#1b1d2e');
    text('PUNTOS', W - 150, 5, '#9fd3ff', 1, 'right', '#1b1d2e');
    text(String(Game.score).padStart(6, '0'), W - 150, 15, '#ffffff', 2, 'right', '#1b1d2e');
    if (Game.timer !== null) {
      text('TIEMPO', W - 46, 5, '#9fd3ff', 1, 'right', '#1b1d2e');
      text(String(Math.ceil(Game.timer)), W - 46, 15, Game.timer < 60 ? '#ff8a7a' : '#ffffff', 2, 'right', '#1b1d2e');
    }
    // Puntos flotantes (en coordenadas del marcador).
    particles.forEach(function (pt) {
      if (pt.kind !== 'text') return;
      var x = (lerp(pt.px, pt.x, alpha) - rcx) * ZOOM;
      var y = (lerp(pt.py, pt.y, alpha) - rcy) * ZOOM;
      if (y < 36) return;
      g.globalAlpha = Math.min(1, (pt.life / pt.max) * 2);
      text(pt.str, Math.round(x), Math.round(y), '#ffffff', 1, 'center', '#1b1d2e');
      g.globalAlpha = 1;
    });
  }

  function panel(x, y, w, h) {
    g.fillStyle = 'rgba(14,16,30,0.82)';
    g.fillRect(x, y, w, h);
    g.fillStyle = '#ffd43a';
    g.fillRect(x, y, w, 2);
    g.fillRect(x, y + h - 2, w, 2);
    g.fillRect(x, y, 2, h);
    g.fillRect(x + w - 2, y, 2, h);
  }

  function drawMenu(key, items, x, y, s) {
    var boxes = [];
    items.forEach(function (it, i) {
      var sel = i === Game.menu;
      var wdt = textWidth(it.label, s);
      var bx = Math.round(x - wdt / 2) - 14;
      var by = y + i * (s * 7 + 14) - 6;
      boxes.push({ x: bx, y: by, w: wdt + 28, h: s * 7 + 12 });
      if (sel) {
        g.fillStyle = 'rgba(255,212,58,0.18)';
        g.fillRect(bx, by, wdt + 28, s * 7 + 12);
        if (Math.floor(Game.frame / 16) % 2 === 0) text('>', bx + 3, y + i * (s * 7 + 14), '#ffd43a', s);
      }
      text(it.label, x, y + i * (s * 7 + 14), sel ? '#ffd43a' : '#ffffff', s, 'center', '#1b1d2e');
    });
    menuBoxes[key] = boxes;
  }

  function blit2(img, x, y, k) {
    g.drawImage(img, Math.round(x), Math.round(y), Math.round(img.width * k), Math.round(img.height * k));
  }

  function render() {
    var sc = Game.scene;
    sctx.setTransform(1, 0, 0, 1, 0, 0);
    if (sc === 'title' || sc === 'options' || sc === 'map' || sc === 'gameover' || sc === 'ending' || !world || !player) {
      g.globalAlpha = 1;
      if (sc === 'title' || sc === 'options') renderTitle(sc);
      else if (sc === 'map') renderMap();
      else if (sc === 'gameover') renderGameOver();
      else if (sc === 'ending') renderEnding();
      else {
        g.fillStyle = '#0e101e';
        g.fillRect(0, 0, W, H);
      }
      sctx.imageSmoothingEnabled = false;
      sctx.drawImage(buf, 0, 0, screen.width, screen.height);
      return;
    }
    var map = world.current;
    renderWorld();
    g.clearRect(0, 0, W, H);
    drawHud();

    if (sc === 'intro') {
      g.fillStyle = '#0e101e';
      g.fillRect(0, 0, W, H);
      text('MUNDO ' + map.id, W / 2, 140, '#ffd43a', 3, 'center');
      text(world.main.name, W / 2, 180, '#ffffff', 2, 'center');
      var spr = (player.power === 2 ? A.ruyFire : A.ruy)[player.power ? 'big' : 'small'].idle.r;
      blit2(spr, W / 2 - 60, 290 - spr.height * 2, 2);
      text('× ' + Game.lives, W / 2 - 10, 262, '#ffffff', 2);
    }
    if (sc === 'pause') {
      g.fillStyle = 'rgba(14,16,30,0.55)';
      g.fillRect(0, 0, W, H);
      panel(W / 2 - 130, 130, 260, 150);
      text('PAUSA', W / 2, 152, '#ffd43a', 3, 'center');
      drawMenu('pause', [{ label: 'CONTINUAR' }, { label: 'VOLVER AL MAPA' }], W / 2, 206, 2);
    }
    if (sc === 'clear' && Game.message) {
      panel(W / 2 - 170, 110, 340, 190);
      text(Game.message.title, W / 2, 136, '#ffd43a', 2, 'center');
      Game.message.lines.forEach(function (l, i) { text(l, W / 2, 180 + i * 24, '#ffffff', 2, 'center'); });
      if (Game.sceneTime > 70 && Math.floor(Game.frame / 20) % 2) text('PULSA SALTAR', W / 2, 270, '#9fd3ff', 1, 'center');
    }
    sctx.imageSmoothingEnabled = false;
    var full = sc !== 'play' || particles.some(function (pt) { return pt.kind === 'text'; });
    if (full) sctx.drawImage(buf, 0, 0, screen.width, screen.height);
    else sctx.drawImage(buf, 0, 0, W, 36, 0, 0, screen.width, Math.round((36 * screen.height) / H));
  }

  function renderTitle(sc) {
    g.imageSmoothingEnabled = false;
    drawBackdrop(g, 'meadow', ZOOM, Game.frame * 0.6, 156, 156, 352, false, W, H);
    var tiles = A.tiles('meadow');
    var gy = Math.round((352 - 156) * ZOOM);
    var ts = Math.round(T * ZOOM);
    var off = Math.round((Game.frame * 0.6 * ZOOM) % ts);
    for (var x = -1; x < W / ts + 1; x++) {
      g.drawImage(tiles.tuft, x * ts - off, gy - Math.round(5 * ZOOM), ts, Math.round(5 * ZOOM));
      g.drawImage(tiles.top[x & 1], x * ts - off, gy, ts, ts);
      for (var r = 1; r < 5; r++) g.drawImage(tiles.ground[(x + r) & 1], x * ts - off, gy + r * ts, ts, ts);
    }
    blit2(A.bush, 150, gy - A.bush.height * ZOOM + 4, ZOOM);
    blit2(A.bush, 330, gy - A.bush.height * ZOOM + 4, ZOOM);
    // Logo
    var bob = Math.round(Math.sin(Game.frame / 30) * 3);
    text('SUPER', W / 2, 40 + bob, '#ffffff', 3, 'center', '#1b1d2e');
    text('RPG BROS.', W / 2, 70 + bob, '#ffd43a', 6, 'center', '#1b1d2e');
    var run = A.ruy.big['run' + (Math.floor(Game.frame / 5) % 6)].r;
    blit2(run, 34, gy - run.height * 2 + 2, 2);
    blit2(A.blob[Math.floor(Game.frame / 8) % 4].l, 468, gy - A.blob[0].l.height * 2 + 2, 2);
    if (sc === 'title') {
      panel(W / 2 - 150, 150, 300, 40 + titleItems().length * 30);
      drawMenu('title', titleItems(), W / 2, 172, 2);
    } else {
      panel(W / 2 - 190, 140, 380, 190);
      text('OPCIONES', W / 2, 156, '#ffd43a', 2, 'center');
      drawMenu('options', optionItems(), W / 2, 196, 2);
      text('MODO TRANQUILO: MÁS VIDAS, SIN TIEMPO Y MÁS LENTO', W / 2, 312, '#9fd3ff', 1, 'center');
    }
    text('MOVER: FLECHAS · SALTAR: Z · CORRER/FUEGO: X · PAUSA: ESC', W / 2, H - 14, '#ffffff', 1, 'center', '#1b1d2e');
    if (Game.message) text(Game.message.title, W / 2, 132, '#ffffff', 1, 'center', '#1b1d2e');
  }

  function renderMap() {
    var names = LEVEL_NAMES || (LEVEL_NAMES = window.SRBLevels.map(function (f) { return f().name; }));
    g.fillStyle = '#3aa6e8';
    g.fillRect(0, 0, W, H);
    // Isla
    g.fillStyle = 'rgba(10,40,90,0.25)';
    g.beginPath();
    g.ellipse(W / 2 + 6, H / 2 + 40, 252, 140, 0, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = '#f2d39e';
    g.beginPath();
    g.ellipse(W / 2, H / 2 + 30, 250, 140, 0, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = '#5cc33f';
    g.beginPath();
    g.ellipse(W / 2, H / 2 + 24, 238, 128, 0, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = '#7cd65a';
    g.beginPath();
    g.ellipse(W / 2 - 20, H / 2 + 6, 200, 96, 0, 0, Math.PI * 2);
    g.fill();
    // Ondas del mar
    g.fillStyle = 'rgba(255,255,255,0.5)';
    for (var i = 0; i < 14; i++) {
      var wx = (i * 83 + Game.frame * 0.3) % (W + 40) - 20;
      g.fillRect(wx, 30 + ((i * 47) % 50), 12, 2);
      g.fillRect((wx + 200) % W, H - 40 - ((i * 31) % 30), 10, 2);
    }
    // Camino
    g.fillStyle = '#e2b77a';
    for (var n = 0; n < MAP_NODES.length - 1; n++) {
      var a = MAP_NODES[n];
      var b = MAP_NODES[n + 1];
      for (var t = 0; t <= 1; t += 0.04) g.fillRect(Math.round(a.x + (b.x - a.x) * t) - 3, Math.round(a.y + (b.y - a.y) * t) - 3, 6, 6);
    }
    MAP_NODES.forEach(function (nd, idx) {
      var open = idx < save.unlocked;
      var done = save.cleared.indexOf('1-' + (idx + 1)) >= 0;
      g.fillStyle = 'rgba(0,0,0,0.25)';
      g.fillRect(nd.x - 12, nd.y - 10, 28, 26);
      g.fillStyle = '#1b1d2e';
      g.fillRect(nd.x - 13, nd.y - 13, 26, 26);
      g.fillStyle = done ? '#ffd43a' : open ? '#e8402f' : '#8a8fa8';
      g.fillRect(nd.x - 11, nd.y - 11, 22, 22);
      g.fillStyle = 'rgba(255,255,255,0.35)';
      g.fillRect(nd.x - 11, nd.y - 11, 22, 3);
      text(String(idx + 1), nd.x, nd.y - 3, '#1b1d2e', 1, 'center');
      text(names[idx], nd.x, nd.y + 20, open ? '#ffffff' : '#c8cde0', 1, 'center', '#1b1d2e');
    });
    var cur = MAP_NODES[Game.levelIndex];
    var hop = Math.abs(Math.round(Math.sin(Game.frame / 10) * 4));
    var spr = A.ruy.small[hop > 2 ? 'jump' : 'idle'].r;
    g.fillStyle = 'rgba(0,0,0,0.3)';
    g.fillRect(cur.x - 10 + hop, cur.y - 15, 20 - hop * 2, 3);
    blit2(spr, cur.x - 18, cur.y - 50 - hop, 2);
    panel(12, 12, W - 24, 34);
    text('MAPA DEL MUNDO', 26, 25, '#ffd43a', 1);
    text('RUY ×' + Game.lives + '   MONEDAS ' + Game.coins, W - 26, 25, '#ffffff', 1, 'right');
    text('<  > ELEGIR NIVEL · SALTAR PARA ENTRAR · ESC MENÚ', W / 2, H - 22, '#ffffff', 1, 'center', '#1b1d2e');
  }

  function renderGameOver() {
    g.fillStyle = '#0e101e';
    g.fillRect(0, 0, W, H);
    var t = Math.min(1, Game.sceneTime / 90);
    text('FIN DEL JUEGO', W / 2, 130 - Math.round((1 - t) * 40), '#e8402f', 4, 'center');
    if (Game.sceneTime >= 180) drawMenu('gameover', [{ label: 'REINTENTAR' }, { label: 'MAPA DEL MUNDO' }], W / 2, 220, 2);
    else text('...', W / 2, 220, '#ffffff', 2, 'center');
  }

  function renderEnding() {
    drawBackdrop(g, 'tower', ZOOM, Game.frame * 0.4, 156, 156, 352, false, W, H);
    panel(60, 90, W - 120, 220);
    text('¡FELICIDADES!', W / 2, 120, '#ffd43a', 3, 'center');
    text('SUPERASTE LOS 4 NIVELES', W / 2, 170, '#ffffff', 2, 'center');
    text('PUNTOS ' + Game.score, W / 2, 210, '#ffffff', 2, 'center');
    var spr = A.ruy.big.jump.r;
    blit2(spr, W / 2 - 18, 236 - Math.abs(Math.round(Math.sin(Game.frame / 8) * 10)), 2);
  }

  // ───────────────────────────── arranque ─────────────────────────────
  // El juego registra métricas con un toque de menús; el iframe lo pide al cerrarse.
  window.SRBGame = { stats: Stats, game: Game };
  // Hooks de prueba (no afectan la partida): permiten verificar el motor sin jugar a mano.
  window.SRBDebug = {
    start: function (i) { Game.lives = 5; startLevel(i || 0); setScene('play'); },
    player: function () { return player; },
    entities: function () { return entities; },
    particles: function () { return particles; },
    clearEnemies: function () { entities = entities.filter(function (e) { return !e.enemy; }); },
    world: function () { return world; },
    press: press,
    release: release,
    releaseAll: function () { keys = {}; pressed = {}; },
    scene: function () { return Game.scene; },
    /** Detiene la simulación automática; con step(n) se avanza a mano (pruebas deterministas). */
    freeze: function (on) { frozen = on !== false; },
    step: function (n) {
      for (var i = 0; i < (n || 1); i++) {
        update();
        pressed = {};
        tap = null;
      }
    },
    /** Coloca a Ruy de pie con los pies en la fila `row` (coordenadas de celda). */
    teleport: function (tx, row) {
      player.x = tx * T + 2;
      player.y = row * T - player.h;
      player.px = player.x;
      player.py = player.y;
      player.vx = 0;
      player.vy = 0;
      player.onGround = false;
      player.goal = null;
      snapCamera();
    },
    setPower: function (n) { setPower(player, n); player.grow = 0; },
    physics: PH,
    cam: function () { return { x: cam.x, y: cam.y, vw: VW, vh: VH }; },
    perf: function (reset) {
      var r = { frames: perf.n, updMs: perf.n ? perf.upd / perf.n : 0, renMs: perf.n ? perf.ren / perf.n : 0, steps: perf.steps };
      if (reset) perf = { upd: 0, ren: 0, n: 0, steps: 0 };
      return r;
    },
  };

  resize();
  requestAnimationFrame(function (t) {
    last = t;
    requestAnimationFrame(frame);
  });
})();
