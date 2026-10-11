/*
 * Super RPG Bros. — motor.
 *
 * Plataformas 2D con física de píxel a 60 Hz fijos: aceleración y fricción al caminar/correr, gravedad, salto de
 * altura variable (con tiempo de gracia al borde y salto anticipado), colisión AABB contra la grilla de 16x16 y
 * plataformas de un sentido. Resolución interna 544x416 escalada sin suavizado.
 *
 * El juego no muestra KPIs: el marcador es el de cualquier plataformas (vidas, monedas, mundo, tiempo). Al salir,
 * envía las métricas de la partida a la plataforma con MoscowleGame (vendor/moscowle-bridge.js).
 */
(function () {
  'use strict';

  var A = window.SRBArt;
  var T = A.T;
  var W = 544;
  var H = 416;
  var COLS = W / T;

  // ───────────────────────────── pantalla ─────────────────────────────
  var screen = document.getElementById('screen');
  var sctx = screen.getContext('2d');
  var buf = document.createElement('canvas');
  buf.width = W;
  buf.height = H;
  var g = buf.getContext('2d');
  g.imageSmoothingEnabled = false;

  function resize() {
    var box = screen.parentElement.getBoundingClientRect();
    var scale = Math.min(box.width / W, box.height / H);
    if (scale >= 1) scale = Math.floor(scale * 4) / 4;
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    screen.style.width = Math.round(W * scale) + 'px';
    screen.style.height = Math.round(H * scale) + 'px';
    screen.width = Math.round(W * scale * dpr);
    screen.height = Math.round(H * scale * dpr);
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

  // ───────────────────────────── física ─────────────────────────────
  var PH = {
    acc: 0.085, runAcc: 0.125, max: 1.55, runMax: 2.75, fric: 0.12, skid: 0.26, air: 0.075,
    grav: 0.36, gravHold: 0.155, jump: 5.25, jumpRun: 5.75, maxFall: 5.6, stomp: 4.4,
    waterGrav: 0.07, waterMaxFall: 1.15, swim: 2.35, waterMax: 1.25,
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
  var cam = { x: 0, y: 0 };

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
    cam.x = clamp(player.x - W * 0.4, 0, map.w * T - W);
    cam.y = clamp(player.y - H * 0.55, 0, map.h * T - H);
  }

  function clamp(v, a, b) {
    return Math.max(a, Math.min(b, v));
  }

  // ───────────────────────────── jugador ─────────────────────────────
  function makePlayer(x, y, power) {
    var p = {
      kind: 'player', x: x, y: y, w: 12, h: power ? 30 : 15, vx: 0, vy: 0, face: 1, power: power || 0,
      onGround: false, coyote: 0, buffer: 0, holding: 0, crouch: false, invuln: 0, anim: 0, state: 'idle',
      dead: false, deadT: 0, warp: null, goal: null, fireCool: 0, inWater: false, grow: 0,
    };
    if (power) p.y -= 15;
    return p;
  }

  function setPower(p, power) {
    var was = p.power;
    p.power = power;
    var newH = power ? 30 : 15;
    if (p.crouch && power) newH = 15;
    p.y += p.h - newH;
    p.h = newH;
    if (power > was) p.grow = 40;
  }

  function hurtPlayer(p) {
    if (p.invuln > 0 || p.dead || p.goal) return;
    Stats.hits++;
    if (p.power > 0) {
      setPower(p, p.power === 2 ? 1 : 0);
      p.invuln = 100;
      Sound.play('hurt');
    } else {
      killPlayer(p);
    }
  }

  function killPlayer(p) {
    if (p.dead) return;
    p.dead = true;
    p.deadT = 0;
    p.vy = -6;
    p.vx = 0;
    Stats.deaths++;
    Sound.music(false);
    Sound.play('die');
  }

  function updatePlayer(p) {
    var map = world.current;
    if (p.dead) {
      p.deadT++;
      if (p.deadT > 30) {
        p.vy = Math.min(p.vy + 0.32, 6);
        p.y += p.vy;
      }
      if (p.deadT > 150) afterDeath();
      return;
    }
    if (p.warp) return updateWarp(p);
    if (p.goal) return updateGoal(p);

    var speedK = save.options.calm ? 0.85 : 1;
    var feet = cell(map, Math.floor((p.x + p.w / 2) / T), Math.floor((p.y + p.h - 2) / T));
    var chest = cell(map, Math.floor((p.x + p.w / 2) / T), Math.floor((p.y + 4) / T));
    p.inWater = isWater(feet) || isWater(chest);

    var dir = (keys.right ? 1 : 0) - (keys.left ? 1 : 0);
    var run = keys.b;
    var wantCrouch = keys.down && p.onGround;
    if (wantCrouch !== p.crouch && p.power) {
      // Agacharse con Ruy grande reduce la caja; al pararse, solo si hay sitio.
      if (wantCrouch) {
        p.y += 15;
        p.h = 15;
        p.crouch = true;
      } else if (!isSolid(cell(map, Math.floor(p.x / T), Math.floor((p.y - 15) / T))) && !isSolid(cell(map, Math.floor((p.x + p.w - 1) / T), Math.floor((p.y - 15) / T)))) {
        p.y -= 15;
        p.h = 30;
        p.crouch = false;
      }
    } else {
      p.crouch = wantCrouch;
    }
    if (p.crouch && p.onGround) dir = 0;

    // Horizontal: aceleración, tope según caminar/correr, fricción y derrape al cambiar de sentido.
    var max = (p.inWater ? PH.waterMax : run ? PH.runMax : PH.max) * speedK;
    var acc = p.onGround ? (run ? PH.runAcc : PH.acc) : PH.air;
    if (dir !== 0) {
      p.face = dir;
      if (p.onGround && p.vx * dir < -0.4) {
        p.vx += dir * PH.skid;
        if (Game.frame % 4 === 0) dust(p.x + p.w / 2, p.y + p.h, 1);
        p.state = 'skid';
      } else {
        p.vx += dir * acc;
      }
      if (Math.abs(p.vx) > max) p.vx = Math.sign(p.vx) * Math.max(max, Math.abs(p.vx) - PH.fric);
    } else if (p.onGround) {
      if (Math.abs(p.vx) <= PH.fric) p.vx = 0;
      else p.vx -= Math.sign(p.vx) * PH.fric;
    }

    // Salto: con tiempo de gracia al dejar el borde y pulsación anticipada antes de aterrizar.
    if (pressed.a) p.buffer = BUFFER;
    else if (p.buffer > 0) p.buffer--;
    if (p.onGround) p.coyote = COYOTE;
    else if (p.coyote > 0) p.coyote--;

    if (p.inWater) {
      if (pressed.a) {
        p.vy = -PH.swim;
        Sound.play('jump');
      }
      p.vy = Math.min(p.vy + PH.waterGrav, PH.waterMaxFall);
    } else {
      if (p.buffer > 0 && p.coyote > 0) {
        p.vy = -(Math.abs(p.vx) > PH.max + 0.3 ? PH.jumpRun : PH.jump);
        p.buffer = 0;
        p.coyote = 0;
        p.holding = 18;
        p.onGround = false;
        Sound.play('jump');
        dust(p.x + p.w / 2, p.y + p.h, 3);
      }
      // Altura variable: mientras se mantiene A al subir, la gravedad es menor; al soltar, el salto se corta.
      var holdingJump = keys.a && p.vy < 0 && p.holding > 0;
      if (p.holding > 0) p.holding--;
      if (!keys.a && p.vy < -2.2) p.vy = -2.2;
      p.vy = Math.min(p.vy + (holdingJump ? PH.gravHold : PH.grav), PH.maxFall);
    }

    // Disparo con la flor de fuego.
    if (p.fireCool > 0) p.fireCool--;
    if (pressed.b && p.power === 2 && p.fireCool === 0 && countFireballs() < 2) {
      entities.push(makeFireball(p.face > 0 ? p.x + p.w : p.x - 8, p.y + (p.crouch ? 4 : 8), p.face));
      p.fireCool = 14;
      Sound.play('fire');
    }

    var wasGround = p.onGround;
    var fallSpeed = p.vy;
    var res = move(p, map, { hidden: true, dropThrough: keys.down && keys.a });
    p.onGround = res.ground;
    if (res.ground && !wasGround && fallSpeed > 3) dust(p.x + p.w / 2, p.y + p.h, 4);
    if (res.ceil) hitBlock(res.ceil.x, res.ceil.y, p);

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
          map.grid[cy][cx] = ' ';
          addCoin(cx * T + 8, cy * T + 8, false);
        }
      }
    }

    // Tubería: de pie sobre una boca con atajo y pulsando abajo.
    if (p.onGround && keys.down) {
      var under = Math.floor((p.y + p.h + 1) / T);
      map.warps.forEach(function (wp) {
        if (wp.y === under && p.x >= wp.x * T + 2 && p.x + p.w <= (wp.x + 2) * T - 2) {
          p.warp = { t: 0, target: wp };
          Sound.play('pipe');
        }
      });
    }

    // Meta
    if (map.flagX !== null && map.flagX !== undefined && p.x + p.w >= map.flagX * T + 6 && !p.goal) {
      p.goal = { t: 0, phase: 'slide' };
      p.vx = 0;
      p.vy = 0;
      p.x = map.flagX * T - p.w + 4;
      Sound.music(false);
      Sound.play('clear');
    }

    // Caída a un foso
    if (p.y > map.h * T + 24) killPlayer(p);

    if (p.invuln > 0) p.invuln--;
    if (p.grow > 0) p.grow--;

    // Animación
    if (!p.onGround) p.state = 'jump';
    else if (p.crouch) p.state = 'crouch';
    else if (p.state !== 'skid' || Math.abs(p.vx) < 0.5 || dir === 0 || p.vx * dir > 0) p.state = Math.abs(p.vx) > 0.15 ? 'run' : 'idle';
    p.anim += Math.abs(p.vx) * 0.12 + 0.02;

    // Punto de control a mitad de los niveles horizontales.
    if (!world.checkpoint && map === world.main && !map.vertical && p.x > (map.w * T) / 2) {
      world.checkpoint = { x: Math.floor(p.x / T), y: Math.floor((p.y + p.h) / T) - 2 };
    }
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
      p.state = 'jump';
      if (p.y >= groundY && gl.t > 20) {
        gl.phase = 'walk';
        p.face = 1;
      }
    } else if (gl.phase === 'walk') {
      p.vx = 1.2;
      p.vy = Math.min(p.vy + PH.grav, PH.maxFall);
      var res = move(p, map);
      p.onGround = res.ground;
      p.state = 'run';
      p.anim += 0.15;
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
    bumps.push({ x: tx, y: ty, t: 0 });
    // Un golpe desde abajo también derriba a los enemigos que estén encima.
    entities.forEach(function (e) {
      if (e.enemy && !e.dead && overlap(e, { x: tx * T, y: ty * T - 4, w: T, h: 4 })) defeatEnemy(e, 'bump');
    });
    if (ch === '?' || ch === 'H') {
      map.grid[ty][tx] = 'U';
      addCoin(tx * T + 8, ty * T - 8, true);
    } else if (ch === 'M') {
      map.grid[ty][tx] = 'U';
      entities.push(makeItem(p.power ? 'flower' : 'mushroom', tx * T, ty * T));
      Sound.play('appear');
    } else if (ch === 'B') {
      if (p.power) {
        map.grid[ty][tx] = ' ';
        for (var i = 0; i < 4; i++) {
          particles.push({ x: tx * T + 4 + (i % 2) * 8, y: ty * T + 4 + Math.floor(i / 2) * 8, vx: (i % 2 ? 1.2 : -1.2), vy: -4 + Math.floor(i / 2) * 1.5, life: 60, color: A.themes[map.theme].brick, size: 5, grav: 0.3 });
        }
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
    if (popped) particles.push({ x: x - 7, y: y, vx: 0, vy: -4, life: 26, coin: true, grav: 0.3 });
    for (var i = 0; i < 5; i++) particles.push({ x: x, y: y, vx: Math.cos(i * 1.26) * 1.4, vy: Math.sin(i * 1.26) * 1.4 - 0.5, life: 18, color: '#fff6c2', size: 2 });
  }

  function dust(x, y, n) {
    for (var i = 0; i < n; i++) {
      particles.push({ x: x + (Math.random() - 0.5) * 8, y: y - 2, vx: (Math.random() - 0.5) * 1.2, vy: -Math.random() * 0.8, life: 18 + Math.random() * 8, color: 'rgba(240,235,220,0.85)', size: 2 + Math.round(Math.random()) });
    }
  }

  // ───────────────────────────── enemigos y objetos ─────────────────────────────
  function makeEnemy(type, x, y) {
    var e = { kind: type, enemy: true, x: x + 1, y: y + 1, w: 14, h: 15, vx: -0.45, vy: 0, dead: false, deadT: 0, anim: 0, active: false, homeY: y };
    if (type === 'bee') {
      e.vx = 0;
      e.fly = true;
      e.h = 13;
    }
    if (type === 'hog') {
      e.vx = -0.4;
      e.spiky = true;
    }
    return e;
  }

  function makeItem(kind, x, y) {
    return { kind: kind, item: true, x: x + 1, y: y, w: 14, h: 15, vx: 0, vy: 0, rise: 16, startY: y };
  }

  function makeFireball(x, y, dir) {
    return { kind: 'fireball', x: x, y: y, w: 8, h: 8, vx: 3.4 * dir, vy: 1, life: 160 };
  }

  function defeatEnemy(e, how) {
    if (e.dead) return;
    e.dead = true;
    e.deadT = 0;
    e.how = how;
    Game.score += 100;
    Stats.score = Game.score;
    if (how === 'stomp') {
      e.vx = 0;
      Stats.stomps++;
      Sound.play('stomp');
    } else {
      e.vy = -3.5;
      e.vx = how === 'fire' ? 0.8 : 0;
      Sound.play('stomp');
    }
  }

  function updateEntity(e) {
    var map = world.current;
    if (e.enemy) {
      if (!e.active) {
        if (e.x < cam.x + W + 48 && e.x > cam.x - 64 && e.y > cam.y - 64 && e.y < cam.y + H + 64) e.active = true;
        else return;
      }
      if (e.dead) {
        e.deadT++;
        if (e.how !== 'stomp') {
          e.vy += 0.3;
          e.y += e.vy;
          e.x += e.vx;
        }
        if (e.deadT > (e.how === 'stomp' ? 30 : 90)) e.gone = true;
        return;
      }
      e.anim += 0.08;
      if (e.fly) {
        // Abeja: flota y, si Ruy está cerca, lo persigue despacio.
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
        e.face = e.vx > 0 ? 1 : -1;
        move(e, map);
      } else {
        e.vy = Math.min(e.vy + PH.grav, PH.maxFall);
        // El erizo no se cae de su plataforma: da la vuelta en el borde.
        if (e.spiky && e.onGround) {
          var ahead = Math.floor((e.vx > 0 ? e.x + e.w + 1 : e.x - 1) / T);
          var below = Math.floor((e.y + e.h + 2) / T);
          var c2 = cell(map, ahead, below);
          if (!isSolid(c2) && c2 !== '=') e.vx = -e.vx;
        }
        var res = move(e, map);
        e.onGround = res.ground;
        if (res.wall) e.vx = -res.wall * Math.abs(e.vx || 0.45) || (res.wall > 0 ? -0.45 : 0.45);
        if (e.vx === 0) e.vx = 0.45 * (Math.random() < 0.5 ? -1 : 1);
        e.face = e.vx > 0 ? 1 : -1;
        if (e.y > map.h * T + 32) e.gone = true;
      }
      // Choque con Ruy: desde arriba lo derrota (salvo el erizo); de frente, daña a Ruy.
      if (player && !player.dead && !player.warp && overlap(player, e)) {
        var fromAbove = player.vy > 0 && player.y + player.h - e.y < 9;
        if (fromAbove && !e.spiky) {
          defeatEnemy(e, 'stomp');
          player.vy = keys.a ? -PH.stomp - 1.2 : -PH.stomp;
          player.holding = 10;
        } else {
          hurtPlayer(player);
        }
      }
      return;
    }

    if (e.item) {
      if (e.rise > 0) {
        e.rise--;
        e.y -= 1;
        if (e.rise === 0 && e.kind === 'mushroom') e.vx = 0.85;
        return;
      }
      if (e.kind === 'mushroom') {
        e.vy = Math.min(e.vy + PH.grav, PH.maxFall);
        var r = move(e, map);
        if (r.wall) e.vx = -r.wall * 0.85;
      }
      if (player && !player.dead && overlap(player, e)) {
        e.gone = true;
        Game.score += 1000;
        if (e.kind === 'mushroom' || player.power === 0) setPower(player, 1);
        else setPower(player, 2);
        Sound.play('power');
      }
      if (e.y > map.h * T + 32) e.gone = true;
      return;
    }

    if (e.kind === 'fireball') {
      e.vy = Math.min(e.vy + 0.32, 4);
      var fr = move(e, map);
      if (fr.ground) e.vy = -3;
      if (fr.wall || --e.life <= 0 || e.x < cam.x - 32 || e.x > cam.x + W + 32) {
        e.gone = true;
        particles.push({ x: e.x, y: e.y, vx: 0, vy: 0, life: 10, color: '#ffd43a', size: 6 });
        return;
      }
      entities.forEach(function (en) {
        if (en.enemy && !en.dead && en.active && overlap(e, en)) {
          defeatEnemy(en, 'fire');
          e.gone = true;
        }
      });
    }
  }

  // ───────────────────────────── bucle principal ─────────────────────────────
  var last = performance.now();
  var acc = 0;
  var STEP = 1000 / 60;

  function frame(now) {
    acc += Math.min(100, now - last);
    last = now;
    pollGamepad();
    while (acc >= STEP) {
      update();
      acc -= STEP;
      pressed = {};
      tap = null;
    }
    render();
    sctx.drawImage(buf, 0, 0, screen.width, screen.height);
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

  function updatePlay() {
    if (pressed.pause || pressed.start) {
      Game.scene = 'pause';
      Game.menu = 0;
      Sound.music(false);
      return;
    }
    updatePlayer(player);
    if (!player) return;
    entities.forEach(updateEntity);
    entities = entities.filter(function (e) { return !e.gone; });
    particles.forEach(function (pt) {
      pt.x += pt.vx;
      pt.y += pt.vy;
      pt.vy += pt.grav || 0;
      pt.life--;
    });
    particles = particles.filter(function (pt) { return pt.life > 0; });
    bumps.forEach(function (b) { b.t++; });
    bumps = bumps.filter(function (b) { return b.t < 10; });

    if (Game.timer !== null && !player.dead && !player.goal && !world.current.isRoom) {
      Game.timer -= 1 / 40;
      if (Game.timer <= 0) {
        Game.timer = 0;
        killPlayer(player);
      }
    }

    // Cámara: zona muerta horizontal; en vertical sigue a Ruy hacia arriba y abajo.
    var map = world.current;
    var targetX = player.x + player.w / 2 - W * 0.42;
    if (targetX > cam.x + 8) cam.x += Math.min(targetX - cam.x - 8, 6);
    else if (targetX < cam.x - 40) cam.x += Math.max(targetX - cam.x + 40, -6);
    cam.x = clamp(cam.x, 0, Math.max(0, map.w * T - W));
    var targetY = player.y + player.h / 2 - H * 0.55;
    cam.y += (targetY - cam.y) * 0.12;
    cam.y = clamp(cam.y, 0, Math.max(0, map.h * T - H));
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

  // ───────────────────────────── dibujo ─────────────────────────────
  function drawBackground(theme, parallaxX, parallaxY) {
    var th = A.themes[theme];
    var grad = g.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, th.sky[0]);
    grad.addColorStop(1, th.sky[1]);
    g.fillStyle = grad;
    g.fillRect(0, 0, W, H);
    var py = parallaxY || 0;
    // Colinas lejanas y cercanas a distinta velocidad (paralaje simple).
    hills(th.hillFar, 0.2, 250, 70, 180, parallaxX, py * 0.2);
    if (th.cloud) clouds(th.cloud, parallaxX * 0.3, py * 0.1);
    hills(th.hillNear, 0.45, 300, 52, 120, parallaxX, py * 0.4, th.hillDot);
  }
  function hills(color, k, base, amp, period, px, py, dot) {
    var off = (px * k) % (period * 2);
    g.fillStyle = color;
    for (var x = -period * 2; x < W + period * 2; x += period * 2) {
      var cx = x - off;
      g.beginPath();
      g.ellipse(cx + period, base - py + 40, period, amp + 40, 0, Math.PI, 0);
      g.fill();
      if (dot) {
        g.fillStyle = dot;
        g.fillRect(cx + period - 20, base - py - 4, 4, 4);
        g.fillRect(cx + period + 12, base - py + 14, 4, 4);
        g.fillStyle = color;
      }
    }
    g.fillRect(0, base - py + 40, W, H);
  }
  function clouds(color, px, py) {
    g.fillStyle = color;
    for (var i = 0; i < 6; i++) {
      var x = ((i * 157 - px) % (W + 120) + W + 120) % (W + 120) - 60;
      var y = 40 + ((i * 53) % 90) - py;
      g.fillRect(x, y + 6, 48, 10);
      g.fillRect(x + 8, y, 22, 8);
      g.fillRect(x + 26, y + 2, 14, 6);
    }
  }

  function drawTiles(map, cx, cy) {
    var tiles = A.tiles(map.theme);
    var x0 = Math.floor(cx / T);
    var y0 = Math.floor(cy / T);
    var shine = Math.floor(Game.frame / 12) % 6;
    shine = shine > 2 ? 0 : shine;
    for (var ty = y0; ty <= y0 + H / T + 1; ty++) {
      for (var tx = x0; tx <= x0 + COLS + 1; tx++) {
        var ch = cell(map, tx, ty);
        if (ch === ' ' || isWater(ch) || ch === 'H') continue;
        var x = tx * T - Math.round(cx);
        var y = ty * T - Math.round(cy);
        for (var b = 0; b < bumps.length; b++) if (bumps[b].x === tx && bumps[b].y === ty) y -= Math.round(Math.sin((bumps[b].t / 10) * Math.PI) * 5);
        var img = null;
        switch (ch) {
          case '#': img = isSolid(cell(map, tx, ty - 1)) || cell(map, tx, ty - 1) === '#' ? tiles.ground : tiles.top; break;
          case 'S': img = tiles.stone; break;
          case 'B': img = tiles.brick; break;
          case '?': case 'M': img = tiles.question[shine]; break;
          case 'U': img = tiles.used; break;
          case '=': img = tiles.platform; break;
          case '^': img = tiles.spikes; break;
          case '[': img = tiles.pipeTL; break;
          case ']': img = tiles.pipeTR; break;
          case '{': img = tiles.pipeL; break;
          case '}': img = tiles.pipeR; break;
          case 'o': img = A.coin[[0, 1, 2, 1][Math.floor(Game.frame / 8) % 4]]; x += 1; y += 2; break;
        }
        if (img) g.drawImage(img, x, y);
      }
    }
  }

  function drawWater(map, cx, cy) {
    var tiles = A.tiles(map.theme);
    var x0 = Math.floor(cx / T);
    var y0 = Math.floor(cy / T);
    var f = Math.floor(Game.frame / 10) % 4;
    for (var ty = y0; ty <= y0 + H / T + 1; ty++) {
      for (var tx = x0; tx <= x0 + COLS + 1; tx++) {
        var ch = cell(map, tx, ty);
        if (ch === '~') g.drawImage(tiles.water[f], tx * T - Math.round(cx), ty * T - Math.round(cy));
        else if (ch === 'w') g.drawImage(tiles.waterDeep, tx * T - Math.round(cx), ty * T - Math.round(cy));
      }
    }
  }

  function drawFlag(map, cx, cy) {
    if (map.flagX === null || map.flagX === undefined) return;
    var x = map.flagX * T + 7 - Math.round(cx);
    var top = map.flagTop * T - Math.round(cy);
    var bottom = (map.flagTop + 10) * T - Math.round(cy);
    g.fillStyle = '#1b1d2e';
    g.fillRect(x - 1, top, 4, bottom - top);
    g.fillStyle = '#e8ecf5';
    g.fillRect(x, top, 2, bottom - top);
    g.fillStyle = '#ffd43a';
    g.fillRect(x - 2, top - 5, 6, 6);
    var flagY = top + 4;
    if (player && player.goal) flagY = Math.min(bottom - 24, player.y - Math.round(cy));
    g.drawImage(A.flag, x - 15, flagY);
  }

  function drawPlayer(p, cx, cy) {
    if (!p) return;
    if (p.invuln > 0 && Math.floor(p.invuln / 3) % 2 === 0) return;
    var set = p.power === 2 ? A.ruyFire : A.ruy;
    var big = p.power > 0 && !(p.grow > 0 && Math.floor(p.grow / 4) % 2 === 0);
    var frames = big ? set.big : set.small;
    var name = p.dead ? 'jump' : p.state;
    if (name === 'run') name = ['run1', 'run2', 'run3', 'run2'][Math.floor(p.anim) % 4];
    var spr = frames[name] || frames.idle;
    var img = p.face < 0 ? spr.l : spr.r;
    var x = Math.round(p.x - 2 - cx);
    var y = Math.round(p.y + p.h - img.height - cy);
    if (p.warp) {
      g.save();
      g.beginPath();
      g.rect(x - 4, 0, 24, Math.round(p.warp.target.y * T - cy));
      g.clip();
      g.drawImage(img, x, y);
      g.restore();
      return;
    }
    g.drawImage(img, x, y);
  }

  function drawEntity(e, cx, cy) {
    var x = Math.round(e.x - cx);
    var y = Math.round(e.y - cy);
    if (x < -32 || x > W + 32 || y < -32 || y > H + 32) return;
    var fr = Math.floor(e.anim * 2) % 2;
    if (e.kind === 'blob') {
      if (e.dead && e.how === 'stomp') g.drawImage(A.blobFlat, x - 1, y - 1);
      else drawFlipped(A.blob[fr], e, x - 1, y - 1);
    } else if (e.kind === 'bee') {
      drawFlipped(A.bee[Math.floor(Game.frame / 4) % 2], e, x - 1, y - 2);
    } else if (e.kind === 'hog') {
      drawFlipped(A.hog[fr], e, x - 1, y - 1);
    } else if (e.kind === 'mushroom') {
      g.drawImage(A.mushroom, x - 1, y - 1);
    } else if (e.kind === 'flower') {
      g.drawImage(A.flower, x - 1, y - 1);
    } else if (e.kind === 'fireball') {
      g.drawImage(A.fireball, x, y);
    }
  }
  function drawFlipped(pairImg, e, x, y) {
    var img = e.face > 0 ? pairImg.r : pairImg.l;
    if (e.dead && e.how !== 'stomp') {
      g.save();
      g.translate(x + 8, y + 8);
      g.scale(1, -1);
      g.drawImage(img, -8, -8);
      g.restore();
      return;
    }
    g.drawImage(img, x, y);
  }

  function drawDeco(map, cx, cy) {
    map.deco.forEach(function (d) {
      var img = d.kind === 'bush' ? A.bush : A.fence;
      var x = d.x * T - Math.round(cx);
      var y = d.y * T - img.height - Math.round(cy) + (d.kind === 'bush' ? 2 : 0);
      if (x > -40 && x < W + 40) g.drawImage(img, x, y);
    });
  }

  function drawParticles(cx, cy) {
    particles.forEach(function (pt) {
      if (pt.coin) {
        g.drawImage(A.coin[Math.floor(pt.life / 3) % 3], Math.round(pt.x - cx), Math.round(pt.y - cy));
        return;
      }
      g.fillStyle = pt.color;
      g.fillRect(Math.round(pt.x - cx), Math.round(pt.y - cy), pt.size, pt.size);
    });
  }

  function drawHud() {
    g.fillStyle = 'rgba(14,16,30,0.55)';
    g.fillRect(0, 0, W, 22);
    var map = world.main;
    text('RUY ×' + Game.lives, 10, 8, '#fff', 1, null, '#1b1d2e');
    g.drawImage(A.coin[0], 116, 5);
    text('×' + String(Game.coins).padStart(2, '0'), 132, 8, '#ffd43a', 1, null, '#1b1d2e');
    text('MUNDO ' + map.id, W / 2, 8, '#fff', 1, 'center', '#1b1d2e');
    text(String(Game.score).padStart(6, '0'), W - 120, 8, '#fff', 1, 'right', '#1b1d2e');
    if (Game.timer !== null) text('TIEMPO ' + Math.ceil(Game.timer), W - 10, 8, Game.timer < 60 ? '#ff8a7a' : '#fff', 1, 'right', '#1b1d2e');
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

  function render() {
    var sc = Game.scene;
    if (sc === 'title' || sc === 'options') return renderTitle(sc);
    if (sc === 'map') return renderMap();
    if (sc === 'gameover') return renderGameOver();
    if (sc === 'ending') return renderEnding();
    if (!world || !player) return;
    var map = world.current;
    var cx = cam.x;
    var cy = cam.y;
    drawBackground(map.theme, cx, map.vertical ? cy * 0.25 : 0);
    drawTiles(map, cx, cy);
    drawFlag(map, cx, cy);
    entities.forEach(function (e) { drawEntity(e, cx, cy); });
    drawPlayer(player, cx, cy);
    drawWater(map, cx, cy);
    drawDeco(map, cx, cy);
    drawParticles(cx, cy);
    drawHud();

    if (sc === 'intro') {
      g.fillStyle = '#0e101e';
      g.fillRect(0, 0, W, H);
      text('MUNDO ' + map.id, W / 2, 150, '#ffd43a', 3, 'center');
      text(world.main.name, W / 2, 190, '#ffffff', 2, 'center');
      var spr = (player.power === 2 ? A.ruyFire : A.ruy)[player.power ? 'big' : 'small'].idle.r;
      g.drawImage(spr, W / 2 - 46, 240 + (player.power ? 0 : 16), spr.width, spr.height);
      text('× ' + Game.lives, W / 2 - 20, 254, '#ffffff', 2);
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
  }

  function renderTitle(sc) {
    drawBackground('meadow', Game.frame * 0.6, 0);
    var tiles = A.tiles('meadow');
    for (var x = 0; x < COLS + 1; x++) {
      g.drawImage(tiles.top, x * T, H - 48);
      g.drawImage(tiles.ground, x * T, H - 32);
      g.drawImage(tiles.ground, x * T, H - 16);
    }
    g.drawImage(A.bush, 40, H - 60);
    g.drawImage(A.bush, 430, H - 60);
    // Logo
    var bob = Math.round(Math.sin(Game.frame / 30) * 3);
    text('SUPER', W / 2, 40 + bob, '#ffffff', 3, 'center', '#1b1d2e');
    text('RPG BROS.', W / 2, 70 + bob, '#ffd43a', 6, 'center', '#1b1d2e');
    var run = A.ruy.big[['run1', 'run2', 'run3', 'run2'][Math.floor(Game.frame / 7) % 4]].r;
    g.drawImage(run, 250, H - 80);
    g.drawImage(A.blob[Math.floor(Game.frame / 20) % 2].l, 300, H - 64);
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
    g.fillStyle = '#f2d39e';
    g.beginPath();
    g.ellipse(W / 2, H / 2 + 30, 250, 140, 0, 0, Math.PI * 2);
    g.fill();
    g.fillStyle = '#5cc33f';
    g.beginPath();
    g.ellipse(W / 2, H / 2 + 24, 238, 128, 0, 0, Math.PI * 2);
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
      g.fillStyle = '#1b1d2e';
      g.fillRect(nd.x - 13, nd.y - 13, 26, 26);
      g.fillStyle = done ? '#ffd43a' : open ? '#e8402f' : '#8a8fa8';
      g.fillRect(nd.x - 11, nd.y - 11, 22, 22);
      text(String(idx + 1), nd.x, nd.y - 3, '#1b1d2e', 1, 'center');
      text(names[idx], nd.x, nd.y + 20, open ? '#ffffff' : '#c8cde0', 1, 'center', '#1b1d2e');
    });
    var cur = MAP_NODES[Game.levelIndex];
    var hop = Math.abs(Math.round(Math.sin(Game.frame / 10) * 4));
    g.drawImage(A.ruy.small.idle.r, cur.x - 8, cur.y - 34 - hop);
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
    drawBackground('tower', Game.frame * 0.4, 0);
    panel(60, 90, W - 120, 220);
    text('¡FELICIDADES!', W / 2, 120, '#ffd43a', 3, 'center');
    text('SUPERASTE LOS 4 NIVELES', W / 2, 170, '#ffffff', 2, 'center');
    text('PUNTOS ' + Game.score, W / 2, 210, '#ffffff', 2, 'center');
    g.drawImage(A.ruy.big.jump.r, W / 2 - 8, 236 - Math.abs(Math.round(Math.sin(Game.frame / 8) * 10)));
  }

  // ───────────────────────────── arranque ─────────────────────────────
  // El juego registra métricas con un toque de menús; el iframe lo pide al cerrarse.
  window.SRBGame = { stats: Stats, game: Game };
  // Hooks de prueba (no afectan la partida): permiten verificar el motor sin jugar a mano.
  window.SRBDebug = {
    start: function (i) { Game.lives = 5; startLevel(i || 0); setScene('play'); },
    player: function () { return player; },
    entities: function () { return entities; },
    clearEnemies: function () { entities = entities.filter(function (e) { return !e.enemy; }); },
    world: function () { return world; },
    press: press,
    release: release,
    scene: function () { return Game.scene; },
  };

  resize();
  requestAnimationFrame(function (t) {
    last = t;
    requestAnimationFrame(frame);
  });
})();
