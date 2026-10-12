/*
 * Super RPG Bros. — arte en píxeles.
 *
 * Los personajes se pintan una sola vez en canvases pequeños con un «pintor de materiales»: cada sprite se
 * describe por zonas (gorra, piel, polerón…) y el pintor les da tres tonos (luz arriba-izquierda, sombra
 * abajo-derecha) y un contorno oscuro limpio. Así cada cuadro de animación sale con el mismo acabado.
 * Las poses de Ruy (correr en 6 cuadros, salto, caída, derrape, agacharse…) se arman con huesos simples.
 * Aquí también viven los mosaicos con biselado, las capas de fondo con paralaje y los brillos/sombras
 * pre-renderizados (nada de degradados por cuadro en el bucle del juego).
 */
(function () {
  'use strict';

  var T = 16;

  function canvas(w, h) {
    var c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    return c;
  }

  function rng(seed) {
    return function () {
      seed = (seed + 0x6d2b79f5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function hex(c) {
    return [parseInt(c.slice(1, 3), 16), parseInt(c.slice(3, 5), 16), parseInt(c.slice(5, 7), 16)];
  }
  function mix(a, b, t) {
    var x = hex(a);
    var y = hex(b);
    var o = '#';
    for (var i = 0; i < 3; i++) o += ('0' + Math.round(x[i] + (y[i] - x[i]) * t).toString(16)).slice(-2);
    return o;
  }
  function rgba(c, a) {
    var x = hex(c);
    return 'rgba(' + x[0] + ',' + x[1] + ',' + x[2] + ',' + a + ')';
  }

  // ───────────────────────────── pintor de materiales ─────────────────────────────
  function Grid(w, h) {
    this.w = w;
    this.h = h;
    this.d = [];
    for (var i = 0; i < w * h; i++) this.d.push(null);
  }
  Grid.prototype.get = function (x, y) {
    if (x < 0 || y < 0 || x >= this.w || y >= this.h) return null;
    return this.d[y * this.w + x];
  };
  Grid.prototype.set = function (x, y, m) {
    x = Math.floor(x);
    y = Math.floor(y);
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.d[y * this.w + x] = m;
    return this;
  };
  Grid.prototype.rect = function (x, y, w, h, m) {
    for (var j = 0; j < h; j++) for (var i = 0; i < w; i++) this.set(x + i, y + j, m);
    return this;
  };
  Grid.prototype.ellipse = function (cx, cy, rx, ry, m, keep) {
    for (var y = Math.floor(cy - ry) - 1; y <= Math.ceil(cy + ry); y++) {
      for (var x = Math.floor(cx - rx) - 1; x <= Math.ceil(cx + rx); x++) {
        var dx = (x + 0.5 - cx) / rx;
        var dy = (y + 0.5 - cy) / ry;
        if (dx * dx + dy * dy <= 1 && (!keep || keep(x, y))) this.set(x, y, m);
      }
    }
    return this;
  };
  Grid.prototype.line = function (x0, y0, x1, y1, b, m) {
    var n = Math.max(Math.abs(x1 - x0), Math.abs(y1 - y0)) * 2 + 1;
    for (var i = 0; i <= n; i++) {
      var t = i / n;
      this.rect(Math.round(x0 + (x1 - x0) * t - (b - 1) / 2), Math.round(y0 + (y1 - y0) * t - (b - 1) / 2), b, b, m);
    }
    return this;
  };
  Grid.prototype.rows = function (rows, ox, oy) {
    for (var y = 0; y < rows.length; y++) {
      for (var x = 0; x < rows[y].length; x++) {
        var ch = rows[y][x];
        if (ch !== '.' && ch !== ' ') this.set(ox + x, oy + y, ch);
      }
    }
    return this;
  };
  /** Igual que line, pero solo pinta sobre píxeles de los materiales indicados (líneas internas). */
  Grid.prototype.lineOver = function (x0, y0, x1, y1, b, m, over) {
    var self = this;
    var tmp = new Grid(this.w, this.h);
    tmp.line(x0, y0, x1, y1, b, m);
    tmp.d.forEach(function (v, i) {
      if (v && over.indexOf(self.d[i]) >= 0) self.d[i] = v;
    });
    return this;
  };
  Grid.prototype.clear = function (x, y) {
    return this.set(x, y, null);
  };

  /**
   * Pasa la grilla a un canvas (1 px de margen para el contorno). mats: { char: { r: [oscuro, medio, claro], t? } | { c: '#color' } }.
   * Sin `t`, el tono sale solo: borde superior claro, borde inferior/derecho oscuro, borde izquierdo claro.
   */
  function finish(G, mats, outline) {
    var c = canvas(G.w + 2, G.h + 2);
    var g = c.getContext('2d');
    function ramp(m) {
      var d = m && mats[m];
      if (!d) return null;
      return d.r || 'detail';
    }
    function same(r, x, y) {
      var o = ramp(G.get(x, y));
      return o === r || o === 'detail';
    }
    for (var y = 0; y < G.h; y++) {
      for (var x = 0; x < G.w; x++) {
        var m = G.get(x, y);
        var d = m && mats[m];
        if (!d) continue;
        var col;
        if (d.c) col = d.c;
        else {
          var t = d.t;
          if (t === undefined) {
            var up = same(d.r, x, y - 1);
            var dn = same(d.r, x, y + 1);
            var lf = same(d.r, x - 1, y);
            var rt = same(d.r, x + 1, y);
            t = !up && dn ? 2 : !dn || !rt ? 0 : !lf ? 2 : 1;
          }
          col = d.r[t];
        }
        g.fillStyle = col;
        g.fillRect(x + 1, y + 1, 1, 1);
      }
    }
    if (outline) {
      var filled = function (x, y) {
        var m = G.get(x, y);
        return !!(m && mats[m]);
      };
      g.fillStyle = outline;
      for (var oy = -1; oy <= G.h; oy++) {
        for (var ox = -1; ox <= G.w; ox++) {
          if (filled(ox, oy)) continue;
          if (filled(ox - 1, oy) || filled(ox + 1, oy) || filled(ox, oy - 1) || filled(ox, oy + 1)) g.fillRect(ox + 1, oy + 1, 1, 1);
        }
      }
    }
    return c;
  }

  function flip(c) {
    var f = canvas(c.width, c.height);
    var g = f.getContext('2d');
    g.translate(c.width, 0);
    g.scale(-1, 1);
    g.drawImage(c, 0, 0);
    return f;
  }
  function pair(c) {
    return { r: c, l: flip(c) };
  }

  /** Sprites escritos a mano con paleta fija (para detalles pequeños). */
  function paint(rows, pal) {
    var c = canvas(rows[0].length, rows.length);
    var g = c.getContext('2d');
    for (var y = 0; y < rows.length; y++) {
      for (var x = 0; x < rows[y].length; x++) {
        var col = pal[rows[y][x]];
        if (!col) continue;
        g.fillStyle = col;
        g.fillRect(x, y, 1, 1);
      }
    }
    return c;
  }

  // ───────────────────────────── Ruy (jugador) ─────────────────────────────
  var RAMP = {
    cap: ['#1d6a2c', '#3dac3c', '#93e15c'],
    capF: ['#9c2318', '#e6402f', '#ff917c'],
    skin: ['#cf855a', '#f6c49a', '#ffe4c9'],
    hair: ['#3a2314', '#5e3b22', '#835838'],
    hood: ['#b5500f', '#f28a26', '#ffc46c'],
    hoodF: ['#a9adc0', '#eceef5', '#ffffff'],
    pants: ['#1a2c74', '#2e51ba', '#5d86ee'],
    pantsF: ['#9c2318', '#e6402f', '#ff917c'],
    shoe: ['#9aa0b6', '#e6e8f0', '#ffffff'],
  };

  function ruyMats(fire) {
    var cap = fire ? RAMP.capF : RAMP.cap;
    var hood = fire ? RAMP.hoodF : RAMP.hood;
    var sleeve = hood.slice();
    var pants = fire ? RAMP.pantsF : RAMP.pants;
    var hips = pants.slice();
    var legs = pants.slice();
    return {
      C: { r: cap }, c: { r: cap, t: 0 }, '*': { r: cap, t: 2 }, Y: { c: fire ? '#ffd43a' : '#ffe066' },
      H: { r: RAMP.hair }, S: { r: RAMP.skin }, s: { r: RAMP.skin, t: 0 }, h: { r: RAMP.skin.slice() }, i: { r: RAMP.skin.slice(), t: 0 },
      P: { c: '#1b1d2e' }, W: { c: '#ffffff' }, R: { c: '#ff8f86' }, M: { c: '#9a3324' },
      O: { r: hood }, o: { r: hood, t: 0 }, Z: { c: fire ? '#e6402f' : '#fff1cf' },
      A: { r: sleeve, t: 1 }, a: { r: sleeve, t: 0 },
      B: { r: hips }, N: { r: legs }, n: { r: legs, t: 0 },
      X: { r: RAMP.shoe }, x: { r: RAMP.shoe, t: 0 },
    };
  }

  // Cabeza (16x10): gorra con visera hacia la derecha, pelo atrás, dos ojos, rubor y boca.
  var HEAD = [
    '.....CCCCC......',
    '...CC**CCCCC....',
    '..CC*CCCCYCCC...',
    '..CCCCCCCCCCCC..',
    '.HHCcccccccccccc',
    '.HHSSSSSSSSSSS..',
    '.HSSSSSSSPSSPS..',
    '.sSSSSSSSPSSPSS.',
    '.HsSSSSRSSSSMS..',
    '..ssSSSSSSSSS...',
  ];
  function headVariant(kind) {
    var h = HEAD.slice();
    if (kind === 'blink') {
      h[6] = '.HSSSSSSSSSSSS..';
      h[7] = '.sSSSSSSSPSSPSS.';
    } else if (kind === 'dead') {
      h[6] = '.HSSSSSSPSPSPS..';
      h[7] = '.sSSSSSSSPSSPSS.';
      h[8] = '.HsSSSSRSSSMMS..';
      h[9] = '..ssSSSSSSSMM...';
    } else if (kind === 'oof') {
      h[8] = '.HsSSSSRSSSMMS..';
    }
    return h;
  }

  // Poses. Coordenadas absolutas de la grilla: k* rodilla, f* pie (tobillo), h* mano. F = extremidad lejana, N = cercana.
  var BIG_POSES = {
    idle: { kF: [6, 24], fF: [5, 28], kN: [9, 24], fN: [9, 28], hF: [3, 17], hN: [12, 17] },
    breath: { bob: 1, kF: [6, 24], fF: [5, 28], kN: [9, 24], fN: [9, 28], hF: [3, 18], hN: [12, 18] },
    blink: { head: 'blink', kF: [6, 24], fF: [5, 28], kN: [9, 24], fN: [9, 28], hF: [3, 17], hN: [12, 17] },
    run0: { kN: [11, 23], fN: [12, 27], kF: [5, 24], fF: [2, 26], hN: [5, 16], hF: [13, 14] },
    run1: { bob: 1, kN: [10, 24], fN: [10, 28], kF: [5, 23], fF: [3, 24], hN: [6, 17], hF: [12, 15] },
    run2: { kN: [8, 24], fN: [7, 28], kF: [9, 22], fF: [7, 25], hN: [9, 18], hF: [8, 17] },
    run3: { kF: [11, 23], fF: [12, 27], kN: [5, 24], fN: [2, 26], hF: [5, 16], hN: [13, 14] },
    run4: { bob: 1, kF: [10, 24], fF: [10, 28], kN: [5, 23], fN: [3, 24], hF: [6, 17], hN: [12, 15] },
    run5: { kF: [8, 24], fF: [7, 28], kN: [9, 22], fN: [7, 25], hF: [9, 18], hN: [8, 17] },
    jump: { kN: [11, 22], fN: [10, 26], kF: [6, 24], fF: [4, 28], hN: [14, 13], hF: [1, 8] },
    fall: { kN: [10, 24], fN: [11, 28], kF: [6, 23], fF: [3, 26], hN: [14, 11], hF: [1, 12] },
    skid: { lean: -1, kN: [12, 24], fN: [13, 28], kF: [7, 24], fF: [5, 28], hN: [13, 11], hF: [1, 14], head: 'oof' },
    swim0: { kN: [10, 24], fN: [11, 27], kF: [6, 23], fF: [2, 25], hN: [14, 13], hF: [13, 15] },
    swim1: { kN: [9, 24], fN: [8, 28], kF: [6, 24], fF: [4, 28], hN: [11, 19], hF: [5, 18] },
    dead: { head: 'dead', kF: [6, 24], fF: [5, 28], kN: [9, 24], fN: [10, 28], hF: [1, 13], hN: [14, 14] },
    crouch: { crouch: true },
  };
  var SMALL_POSES = {
    idle: { fF: [5, 14], fN: [9, 14], hF: [3, 12], hN: [12, 12] },
    breath: { bob: 1, fF: [5, 14], fN: [9, 14], hF: [3, 13], hN: [12, 13] },
    blink: { head: 'blink', fF: [5, 14], fN: [9, 14], hF: [3, 12], hN: [12, 12] },
    run0: { fN: [11, 14], fF: [2, 13], hN: [4, 12], hF: [13, 11] },
    run1: { bob: 1, fN: [10, 14], fF: [4, 13], hN: [5, 12], hF: [12, 12] },
    run2: { fN: [7, 14], fF: [8, 13], hN: [8, 13], hF: [8, 12] },
    run3: { fF: [11, 14], fN: [2, 13], hF: [4, 12], hN: [13, 11] },
    run4: { bob: 1, fF: [10, 14], fN: [4, 13], hF: [5, 12], hN: [12, 12] },
    run5: { fF: [7, 14], fN: [8, 13], hF: [8, 13], hN: [8, 12] },
    jump: { fN: [10, 13], fF: [4, 14], hN: [14, 10], hF: [1, 7] },
    fall: { fN: [11, 14], fF: [3, 13], hN: [14, 9], hF: [1, 10] },
    skid: { lean: -1, fN: [12, 14], fF: [5, 14], hN: [13, 9], hF: [1, 11], head: 'oof' },
    swim0: { fN: [11, 13], fF: [2, 13], hN: [14, 11], hF: [13, 12] },
    swim1: { fN: [8, 14], fF: [4, 14], hN: [11, 13], hF: [5, 13] },
    dead: { head: 'dead', fF: [5, 14], fN: [10, 14], hF: [1, 4], hN: [14, 4] },
    crouch: { crouch: true },
  };

  function limbArm(G, sh, hand, sleeve, skin, b, edge) {
    if (edge) G.lineOver(sh[0], sh[1], hand[0], hand[1], b + 2, edge, ['O']);
    G.line(sh[0], sh[1], hand[0], hand[1], b, sleeve);
    G.rect(hand[0], hand[1], 2, 2, skin);
  }

  function drawBigRuy(pose) {
    var G = new Grid(16, 30);
    var b = pose.bob || 0;
    var ln = pose.lean || 0;
    if (pose.crouch) {
      G.rect(2, 26, 5, 2, 'x').rect(9, 27, 6, 2, 'X');
      G.line(5, 25, 4, 26, 3, 'n');
      G.rect(2, 20, 12, 6, 'O').clear(2, 20).clear(13, 20);
      G.rect(4, 25, 9, 2, 'B');
      G.line(10, 24, 12, 26, 3, 'N');
      G.rows(HEAD, 0, 11);
      limbArm(G, [11, 21], [12, 24], 'A', 'h', 2);
      return G;
    }
    var hipY = 19 + b;
    G.line(6 + ln, hipY, pose.kF[0], pose.kF[1], 3, 'n');
    G.line(pose.kF[0], pose.kF[1], pose.fF[0], pose.fF[1] - 1, 3, 'n');
    G.rect(pose.fF[0] - 1, pose.fF[1], 5, 2, 'x');
    limbArm(G, [5 + ln, 12 + b], pose.hF, 'a', 'i', 2);
    G.rect(3 + ln, 10 + b, 10, 9, 'O').clear(3 + ln, 10 + b).clear(12 + ln, 10 + b);
    G.rect(5 + ln, 15 + b, 6, 1, 'o');
    G.rect(4 + ln, 10 + b, 8, 1, 'o');
    G.rect(4 + ln, hipY, 8, 2, 'B');
    G.rows(headVariant(pose.head), ln, b);
    G.line(9 + ln, hipY, pose.kN[0], pose.kN[1], 3, 'N');
    G.line(pose.kN[0], pose.kN[1], pose.fN[0], pose.fN[1] - 1, 3, 'N');
    G.rect(pose.fN[0] - 1, pose.fN[1], 5, 2, 'X');
    limbArm(G, [10 + ln, 12 + b], pose.hN, 'A', 'h', 2, 'o');
    return G;
  }

  function drawSmallRuy(pose) {
    var G = new Grid(16, 16);
    var b = pose.bob || 0;
    var ln = pose.lean || 0;
    if (pose.crouch) {
      G.rect(3, 15, 3, 1, 'x').rect(9, 15, 4, 1, 'X');
      G.rect(3, 12, 10, 3, 'O').clear(3, 12).clear(12, 12);
      G.rect(4, 14, 8, 1, 'B');
      G.rows(HEAD, 0, 4);
      G.rect(11, 13, 2, 1, 'h');
      return G;
    }
    G.line(5 + ln, 13, pose.fF[0], pose.fF[1], 2, 'n');
    G.rect(pose.fF[0] - 1, pose.fF[1] + 1, 3, 1, 'x');
    limbArm(G, [5 + ln, 11], pose.hF, 'a', 'i', 1);
    G.rect(4 + ln, 10, 8, 3, 'O').clear(4 + ln, 10).clear(11 + ln, 10);
    G.rect(4 + ln, 13, 8, 1, 'B');
    G.rows(headVariant(pose.head), ln, b);
    G.line(9 + ln, 13, pose.fN[0], pose.fN[1], 2, 'N');
    G.rect(pose.fN[0] - 1, pose.fN[1] + 1, 3, 1, 'X');
    limbArm(G, [10 + ln, 11], pose.hN, 'A', 'h', 1);
    return G;
  }

  function makeRuy(fire) {
    var mats = ruyMats(fire);
    var out = '#1b1d2e';
    var small = {};
    var big = {};
    Object.keys(BIG_POSES).forEach(function (k) {
      big[k] = pair(finish(drawBigRuy(BIG_POSES[k]), mats, out));
      small[k] = pair(finish(drawSmallRuy(SMALL_POSES[k]), mats, out));
    });
    // Nombres antiguos (menús): idle, jump y run1..run3 siguen existiendo.
    [small, big].forEach(function (s) {
      s.run1 = s.run1 || s.run0;
    });
    return { small: small, big: big };
  }

  // ───────────────────────────── enemigos ─────────────────────────────
  var BLOB_M = {
    V: { r: ['#5a2b9e', '#8b52dc', '#c39bf4'] }, v: { r: ['#5a2b9e', '#8b52dc', '#c39bf4'], t: 0 },
    E: { c: '#f3e9ff' }, W: { c: '#ffffff' }, P: { c: '#1d1030' }, M: { c: '#3a1450' },
    F: { r: ['#b06a10', '#f2b33a', '#ffe07a'] },
  };
  function blobFrame(rx, ry, step, flat) {
    var G = new Grid(16, 14);
    var cy = 13 - ry;
    if (!flat) {
      G.ellipse(4.5 + step, 12.6, 2, 1.2, 'F');
      G.ellipse(11.5 - step, 12.6, 2, 1.2, 'F');
    }
    G.ellipse(8, cy + 0.5, rx, ry, 'V', function (x, y) { return y <= 12; });
    G.rect(Math.round(8 - rx + 1), Math.round(cy + 0.5), Math.round(rx * 2 - 2), Math.max(0, 12 - Math.round(cy + 0.5)), 'V');
    if (flat) {
      G.rect(4, 11, 2, 1, 'P').rect(10, 11, 2, 1, 'P');
      return G;
    }
    var ey = Math.round(cy - 1);
    G.rect(8, ey, 2, 3, 'W').rect(11, ey, 2, 3, 'W');
    G.rect(9, ey + 1, 1, 2, 'P').rect(12, ey + 1, 1, 2, 'P');
    G.rect(9, ey + 4, 3, 1, 'M');
    G.set(4, Math.round(cy - ry * 0.55), 'E').set(5, Math.round(cy - ry * 0.75), 'E').set(4, Math.round(cy - ry * 0.3), 'E');
    return G;
  }

  var BEE_M = {
    Y: { r: ['#c48a10', '#f8c630', '#fff08a'] }, K: { c: '#2a1d10' }, k: { c: '#2a1d10' },
    w: { r: ['#9fcbe8', '#d9f1ff', '#ffffff'] }, W: { c: '#ffffff' }, P: { c: '#1d1a12' }, R: { c: '#ff9a86' },
  };
  function beeFrame(wing) {
    var G = new Grid(16, 14);
    var wy = [2, 4, 6][wing];
    G.ellipse(6, wy, 3, 2.2, 'w');
    G.set(1, 9, 'K').set(2, 9, 'K');
    G.ellipse(7.5, 9, 5.5, 4, 'Y');
    G.rect(5, 5, 1, 8, 'K').rect(8, 5, 1, 8, 'K');
    G.ellipse(9.5, wy + 0.5, 3, 2.4, 'w');
    G.rect(10, 7, 3, 3, 'W').rect(12, 8, 1, 2, 'P');
    G.set(10, 11, 'R');
    G.set(12, 4, 'K').set(13, 3, 'K');
    return G;
  }

  var HOG_M = {
    Q: { r: ['#6f6f86', '#b9b9cc', '#ececf6'] }, M: { r: ['#5e3a1c', '#8c5a30', '#b98250'] },
    F: { r: ['#c48f60', '#f1c79a', '#ffe5c4'] }, P: { c: '#24170c' }, W: { c: '#ffffff' }, N: { c: '#e2574c' },
    K: { r: ['#2e1d0e', '#4a3018', '#6a4828'] },
  };
  function hogFrame(step) {
    var G = new Grid(18, 13);
    var l = [[3, 6, 10, 13], [4, 5, 11, 12], [5, 4, 12, 11], [4, 5, 11, 12]][step];
    G.rect(l[0], 11, 2, 2, 'K').rect(l[2], 11, 2, 2, 'K');
    G.ellipse(8, 8, 7.5, 5, 'Q', function (x, y) { return y <= 10; });
    for (var i = 0; i < 6; i++) G.line(2 + i * 2, 5 - (i % 2), 1 + i * 2, 2 - (i % 2) + (i === 0 ? 2 : 0), 1, 'Q');
    G.ellipse(8, 9, 5.5, 2.6, 'M', function (x, y) { return y <= 10; });
    G.ellipse(13, 8.5, 3.2, 3, 'F');
    G.rect(15, 9, 2, 2, 'F').set(17, 9, 'N');
    G.rect(13, 7, 1, 2, 'P').set(13, 6, 'W');
    G.rect(l[1], 11, 2, 2, 'K').rect(l[3], 11, 2, 2, 'K');
    return G;
  }

  // ───────────────────────────── objetos ─────────────────────────────
  var ITEM_M = {
    R: { r: ['#a02218', '#e8402f', '#ff8a72'] }, E: { c: '#fff4e4' }, S: { r: ['#c9a272', '#f4dcb5', '#fff3dc'] },
    P: { c: '#2a1a12' }, G: { r: ['#1f6b26', '#3fa33a', '#8fd94a'] }, O: { r: ['#c45412', '#f28a26', '#ffc46c'] },
    Y: { r: ['#d29a12', '#ffd43a', '#fff4a0'] }, R2: { c: '#ff8f86' },
  };
  function mushroom() {
    var G = new Grid(16, 15);
    G.rect(4, 8, 8, 6, 'S');
    G.ellipse(8, 7.5, 7.6, 6.5, 'R', function (x, y) { return y <= 8; });
    G.ellipse(8, 3.5, 2, 1.6, 'E').ellipse(2.6, 6, 1.2, 1.6, 'E').ellipse(13.4, 6, 1.2, 1.6, 'E');
    G.rect(6, 10, 1, 2, 'P').rect(9, 10, 1, 2, 'P');
    return G;
  }
  function flower(sway) {
    var G = new Grid(16, 16);
    G.line(8, 9, 8, 15, 2, 'G');
    G.ellipse(4.5, 12.5, 2.6, 1.5, 'G').ellipse(11.5, 13.5, 2.6, 1.5, 'G');
    var cx = 8 + sway;
    for (var i = 0; i < 6; i++) {
      var a = (i / 6) * Math.PI * 2;
      G.ellipse(cx + Math.cos(a) * 3.8, 5.5 + Math.sin(a) * 3.4, 2.2, 2.2, 'O');
    }
    G.ellipse(cx, 5.5, 2.8, 2.6, 'Y');
    G.set(cx - 1, 5, 'P').set(cx + 1, 5, 'P');
    return G;
  }

  var COIN_M = { Y: { r: ['#c98a0c', '#ffd43a', '#fff4b0'] }, y: { r: ['#c98a0c', '#ffd43a', '#fff4b0'], t: 0 }, W: { c: '#fffbe0' } };
  function coinFrame(rx) {
    var G = new Grid(12, 14);
    G.ellipse(6, 7, rx, 6.5, 'Y');
    if (rx >= 3) {
      G.rect(6, 4, 1, 6, 'y');
      G.set(Math.round(6 - rx + 1.5), 4, 'W').set(Math.round(6 - rx + 1.5), 5, 'W');
    } else if (rx >= 1.5) G.set(5, 4, 'W');
    return G;
  }

  var FIRE_M = { R: { r: ['#c42a10', '#ff5a1f', '#ff9a3a'] }, Y: { c: '#ffd43a' }, W: { c: '#fff6c2' } };
  function fireFrame(f) {
    var G = new Grid(8, 8);
    G.ellipse(4, 4, 3.6, 3.6, 'R');
    var a = (f / 4) * Math.PI * 2;
    G.set(4 + Math.round(Math.cos(a) * 3.6), 4 + Math.round(Math.sin(a) * 3.6), 'R');
    G.set(4 + Math.round(Math.cos(a + Math.PI) * 3.6), 4 + Math.round(Math.sin(a + Math.PI) * 3.6), 'R');
    G.ellipse(4, 4, 2.2, 2.2, 'Y');
    G.rect(3, 3, 2, 2, 'W');
    return G;
  }

  // ───────────────────────────── tiles ─────────────────────────────
  function tile(draw, w, h) {
    var c = canvas(w || T, h || T);
    draw(c.getContext('2d'), c);
    return c;
  }
  function rect(g, color, x, y, w, h) {
    g.fillStyle = color;
    g.fillRect(x, y, w, h);
  }

  function themeTiles(th, name) {
    var t = {};
    var R = rng(name.length * 977 + 13);
    function dirt(g, seed) {
      var r = rng(seed);
      rect(g, th.dirt, 0, 0, T, T);
      for (var y = 0; y < T; y++) {
        for (var x = 0; x < T; x++) {
          var v = r();
          if (v < 0.09) rect(g, th.dirtDark, x, y, 1, 1);
          else if (v > 0.95) rect(g, th.dirtLight, x, y, 1, 1);
        }
      }
      for (var i = 0; i < 3; i++) {
        var px = Math.floor(r() * 12) + 1;
        var py = Math.floor(r() * 12) + 2;
        rect(g, mix(th.dirtDark, '#000000', 0.2), px, py + 1, 3, 1);
        rect(g, th.dirtDark, px + 2, py, 1, 1);
        rect(g, th.dirtLight, px, py, 2, 1);
      }
    }
    t.ground = [tile(function (g) { dirt(g, 11); }), tile(function (g) { dirt(g, 29); })];
    t.top = [0, 1].map(function (v) {
      return tile(function (g) {
        dirt(g, 41 + v * 7);
        var r = rng(77 + v);
        rect(g, mix(th.dirtDark, '#000000', 0.15), 0, 5, T, 2);
        rect(g, th.grass, 0, 0, T, 5);
        for (var x = 0; x < T; x++) {
          var drip = Math.floor(r() * 3);
          rect(g, th.grassDark, x, 4, 1, 1 + drip);
          if (r() < 0.3) rect(g, th.grassLight, x, 1 + Math.floor(r() * 2), 1, 1);
        }
        rect(g, th.grassLight, 0, 0, T, 1);
        rect(g, mix(th.grassLight, '#ffffff', 0.35), Math.floor(r() * 10), 0, 3, 1);
      });
    });
    t.tuft = tile(function (g) {
      var r = rng(5);
      for (var x = 0; x < T; x++) {
        var hgt = r() < 0.45 ? Math.floor(r() * 3) + 1 : 0;
        if (hgt) {
          rect(g, th.grass, x, 5 - hgt, 1, hgt);
          rect(g, th.grassLight, x, 5 - hgt, 1, 1);
        }
      }
    }, T, 5);
    t.brick = tile(function (g) {
      var mortar = mix(th.brickDark, '#000000', 0.3);
      rect(g, mortar, 0, 0, T, T);
      var bricks = [[0, 0, 7, 7], [8, 0, 8, 7], [0, 8, 3, 7], [4, 8, 7, 7], [12, 8, 4, 7]];
      bricks.forEach(function (b, i) {
        var base = i % 2 ? th.brick : mix(th.brick, th.brickDark, 0.12);
        rect(g, base, b[0], b[1], b[2], b[3]);
        rect(g, th.brickLight, b[0], b[1], b[2], 1);
        rect(g, mix(th.brickLight, th.brick, 0.5), b[0], b[1], 1, b[3]);
        rect(g, th.brickDark, b[0], b[1] + b[3] - 1, b[2], 1);
        rect(g, mix(th.brickDark, th.brick, 0.4), b[0] + b[2] - 1, b[1] + 1, 1, b[3] - 1);
        rect(g, mix(th.brick, th.brickDark, 0.35), b[0] + 2 + (i % 3), b[1] + 3, 1, 1);
      });
    });
    t.stone = tile(function (g) {
      var r = rng(31);
      rect(g, th.stone, 0, 0, T, T);
      for (var y = 1; y < 15; y++) for (var x = 1; x < 15; x++) if (r() < 0.08) rect(g, mix(th.stone, th.stoneDark, 0.4), x, y, 1, 1);
      rect(g, th.stoneLight, 0, 0, T, 1);
      rect(g, th.stoneLight, 0, 0, 1, T);
      rect(g, mix(th.stoneLight, '#ffffff', 0.4), 1, 1, 4, 1);
      rect(g, th.stoneDark, 0, 15, T, 1);
      rect(g, th.stoneDark, 15, 0, 1, T);
      rect(g, mix(th.stoneDark, th.stone, 0.5), 1, 14, 14, 1);
      rect(g, mix(th.stoneDark, '#000000', 0.25), 15, 15, 1, 1);
      rect(g, th.stoneDark, 6, 5, 1, 3);
      rect(g, th.stoneDark, 7, 8, 2, 1);
      rect(g, th.stoneLight, 7, 5, 1, 2);
    });
    t.used = tile(function (g) {
      rect(g, '#3a2410', 0, 0, T, T);
      rect(g, '#a8763e', 1, 1, 14, 14);
      rect(g, '#c9955a', 1, 1, 14, 1);
      rect(g, '#c9955a', 1, 1, 1, 14);
      rect(g, '#6e4a22', 1, 14, 14, 1);
      rect(g, '#6e4a22', 14, 1, 1, 14);
      [[3, 3], [12, 3], [3, 12], [12, 12]].forEach(function (p) {
        rect(g, '#5a3a18', p[0], p[1], 1, 1);
        rect(g, '#d8aa6a', p[0] - 1, p[1] - 1, 1, 1);
      });
    });
    t.question = [0, 1, 2, 3].map(function (shine) {
      return tile(function (g) {
        rect(g, '#4a2a08', 0, 0, T, T);
        rect(g, '#f5b225', 1, 1, 14, 14);
        rect(g, '#ffe58a', 1, 1, 14, 1);
        rect(g, '#ffd35a', 1, 2, 14, 1);
        rect(g, '#ffe58a', 1, 1, 1, 14);
        rect(g, '#c7780f', 1, 14, 14, 1);
        rect(g, '#d98a14', 14, 1, 1, 14);
        [[3, 3], [12, 3], [3, 12], [12, 12]].forEach(function (p) {
          rect(g, '#9a5a0a', p[0], p[1], 1, 1);
        });
        var glyph = [[6, 4, 4, 1], [5, 5, 2, 2], [9, 5, 2, 3], [7, 8, 3, 1], [7, 9, 2, 2], [7, 12, 2, 1]];
        glyph.forEach(function (q) { rect(g, '#9a5208', q[0] + 1, q[1] + 1, q[2], q[3]); });
        glyph.forEach(function (q) { rect(g, '#fff6d8', q[0], q[1], q[2], q[3]); });
        if (shine > 0) {
          var sx = shine * 5 - 4;
          g.fillStyle = 'rgba(255,255,240,0.55)';
          for (var y = 1; y < 15; y++) {
            var x = sx + (14 - y) * 0.5;
            if (x >= 1 && x < 14) g.fillRect(Math.floor(x), y, 2, 1);
          }
        }
      });
    });
    t.platform = tile(function (g) {
      rect(g, th.wood, 0, 0, T, 6);
      rect(g, th.woodLight, 0, 0, T, 1);
      rect(g, mix(th.woodLight, th.wood, 0.5), 0, 1, T, 1);
      rect(g, th.woodDark, 3, 3, 4, 1);
      rect(g, th.woodDark, 9, 2, 3, 1);
      rect(g, th.woodDark, 11, 4, 3, 1);
      rect(g, th.woodDark, 0, 5, T, 1);
      rect(g, mix(th.woodDark, '#000000', 0.45), 0, 6, T, 1);
      rect(g, mix(th.woodDark, '#000000', 0.2), 15, 1, 1, 5);
      rect(g, '#e8e2d4', 1, 2, 1, 1);
      rect(g, '#e8e2d4', 13, 2, 1, 1);
    });
    var PIPE = ['#0f2a14', '#1c6424', '#2f8a33', '#5fc048', '#bff59a', '#7fd65a', '#4fb23f', '#3fa33a'];
    function pipeCol(x) {
      if (x <= 0 || x >= 31) return PIPE[0];
      if (x === 1) return PIPE[1];
      if (x === 2) return PIPE[2];
      if (x === 3) return PIPE[3];
      if (x === 4 || x === 5) return PIPE[4];
      if (x === 6) return PIPE[5];
      if (x < 16) return PIPE[6];
      if (x < 22) return PIPE[7];
      if (x < 27) return PIPE[2];
      return PIPE[1];
    }
    function pipeTile(half, lip) {
      return tile(function (g) {
        for (var x = 0; x < T; x++) {
          var gx = half * T + x;
          if (lip) {
            rect(g, pipeCol(gx), x, 1, 1, 13);
            rect(g, PIPE[0], x, 0, 1, 1);
            rect(g, PIPE[0], x, 15, 1, 1);
            rect(g, mix(pipeCol(gx), '#ffffff', 0.35), x, 1, 1, 1);
            rect(g, mix(pipeCol(gx), '#000000', 0.35), x, 13, 1, 2);
          } else {
            var bx = gx < 2 || gx > 29 ? -1 : Math.round(((gx - 2) / 27) * 31);
            if (bx < 0) continue;
            rect(g, gx === 2 || gx === 29 ? PIPE[0] : pipeCol(bx), x, 0, 1, T);
          }
        }
        if (!lip) {
          g.fillStyle = 'rgba(0,0,0,0.18)';
          g.fillRect(half ? 0 : 3, 0, half ? 13 : 13, 2);
        }
      });
    }
    t.pipeTL = pipeTile(0, true);
    t.pipeTR = pipeTile(1, true);
    t.pipeL = pipeTile(0, false);
    t.pipeR = pipeTile(1, false);
    t.spikes = tile(function (g) {
      for (var i = 0; i < 4; i++) {
        for (var y = 0; y < 8; y++) {
          var half = Math.floor((y + 1) / 2);
          var x0 = i * 4 + 2 - half;
          rect(g, '#6a6a80', x0, 7 + y, half * 2, 1);
          rect(g, '#d6d6e6', x0, 7 + y, half, 1);
        }
        rect(g, '#ffffff', i * 4 + 1, 7, 1, 1);
      }
      rect(g, '#3e3e52', 0, 15, T, 1);
    });
    t.water = [0, 1, 2, 3].map(function (f) {
      return tile(function (g) {
        rect(g, 'rgba(40,130,225,0.55)', 0, 0, T, T);
        rect(g, 'rgba(20,90,190,0.25)', 0, 8, T, 8);
        for (var x = 0; x < T; x++) {
          var y = Math.round(2 + Math.sin(((x + f * 4) / 16) * Math.PI * 2) * 1.5);
          rect(g, 'rgba(220,246,255,0.95)', x, y, 1, 1);
          rect(g, 'rgba(160,220,255,0.6)', x, y + 1, 1, 1);
        }
        rect(g, 'rgba(200,240,255,0.45)', (f * 5) % 12, 9, 4, 1);
        rect(g, 'rgba(200,240,255,0.3)', (f * 5 + 7) % 13, 12, 3, 1);
      });
    });
    t.waterDeep = [0, 1, 2, 3].map(function (f) {
      return tile(function (g) {
        rect(g, 'rgba(22,92,190,0.7)', 0, 0, T, T);
        g.fillStyle = 'rgba(150,215,255,0.16)';
        for (var x = 0; x < T; x++) {
          var y = Math.round(8 + Math.sin(((x * 2 + f * 8) / 32) * Math.PI * 2) * 4);
          g.fillRect(x, y, 1, 1);
        }
      });
    });
    // Oclusión ambiental (sombra suave pixelada) para celdas vacías junto a bloques.
    t.aoTop = tile(function (g) {
      [0.34, 0.22, 0.13, 0.06].forEach(function (a, i) { g.fillStyle = 'rgba(8,6,24,' + a + ')'; g.fillRect(0, i * 2, T, 2); });
    });
    t.aoTopSoft = tile(function (g) {
      [0.2, 0.12, 0.06].forEach(function (a, i) { g.fillStyle = 'rgba(8,6,24,' + a + ')'; g.fillRect(0, i * 2, T, 2); });
    });
    t.aoPlank = tile(function (g) {
      [0.22, 0.08].forEach(function (a, i) { g.fillStyle = 'rgba(8,6,24,' + a + ')'; g.fillRect(1, 7 + i, T - 2, 1); });
    });
    t.aoLeft = tile(function (g) {
      [0.2, 0.11, 0.05].forEach(function (a, i) { g.fillStyle = 'rgba(8,6,24,' + a + ')'; g.fillRect(i * 2, 0, 2, T); });
    });
    t.aoRight = tile(function (g) {
      [0.2, 0.11, 0.05].forEach(function (a, i) { g.fillStyle = 'rgba(8,6,24,' + a + ')'; g.fillRect(T - 2 - i * 2, 0, 2, T); });
    });
    t.debris = tile(function (g) {
      rect(g, mix(th.brickDark, '#000000', 0.3), 0, 0, 6, 6);
      rect(g, th.brick, 1, 1, 4, 4);
      rect(g, th.brickLight, 1, 1, 4, 1);
      rect(g, th.brickDark, 1, 4, 4, 1);
    }, 6, 6);
    void R;
    return t;
  }

  var THEMES = {
    meadow: {
      sky: ['#3fb4f4', '#bdeeff'], skyHigh: '#2a7fd6', haze: '#cfefff', hillFar: '#7ccf8a', hillNear: '#4fae5c', hillDot: '#3a8f48', cloud: '#ffffff',
      dirt: '#c8834a', dirtDark: '#9a5a2c', dirtLight: '#e2a46e', grass: '#5cc33f', grassLight: '#a2ee6e', grassDark: '#3a8f2a',
      brick: '#d8693a', brickDark: '#8f3a18', brickLight: '#f39a6a', wood: '#b9824a', woodLight: '#e3b27a', woodDark: '#7a4f24',
      stone: '#9aa0b8', stoneDark: '#666b85', stoneLight: '#c8cde0',
      far: '#8fb8d8', mid: '#62b86e', near: '#3f9a50', trees: '#2f7e3e', rays: true, vignette: 0.26,
    },
    cave: {
      sky: ['#0d1230', '#262c5c'], skyHigh: '#070a1e', haze: '#2a3266', hillFar: '#1e2552', hillNear: '#262f66', hillDot: '#34407e', cloud: null,
      dirt: '#5d6aa8', dirtDark: '#3c4680', dirtLight: '#8590cc', grass: '#4fb2c9', grassLight: '#a4eaf5', grassDark: '#2f7c90',
      brick: '#4a66c9', brickDark: '#25357a', brickLight: '#8aa2f2', wood: '#9a7a5a', woodLight: '#c9a57e', woodDark: '#5e4428',
      stone: '#6e76a8', stoneDark: '#454c7a', stoneLight: '#a2aad6',
      far: '#1b2150', mid: '#232b62', near: '#151a40', crystals: '#7fe8ff', vignette: 0.5, dark: true,
    },
    tower: {
      sky: ['#ff8a5c', '#ffd98a'], skyHigh: '#5b3a8c', haze: '#ffd0a0', hillFar: '#e98b6a', hillNear: '#c96a52', hillDot: '#a8513f', cloud: '#fff2df',
      dirt: '#a88466', dirtDark: '#7a5c44', dirtLight: '#c9a688', grass: '#7cc35a', grassLight: '#b8ec8a', grassDark: '#4f8f36',
      brick: '#b9715a', brickDark: '#7a3f2c', brickLight: '#e0a088', wood: '#a46a3a', woodLight: '#d89a62', woodDark: '#6a4020',
      stone: '#c2b4a4', stoneDark: '#8f8070', stoneLight: '#e4d8ca',
      far: '#e9a07e', mid: '#c46e5a', near: '#8a4a44', sun: true, vignette: 0.3,
    },
    lake: {
      sky: ['#3aa8e4', '#dff6ff'], skyHigh: '#2a7fd6', haze: '#e4f7ff', hillFar: '#88d0b8', hillNear: '#56b08e', hillDot: '#3c8a6c', cloud: '#ffffff',
      dirt: '#d9b27a', dirtDark: '#a8824e', dirtLight: '#f2d39e', grass: '#4fcf7a', grassLight: '#9ff2b6', grassDark: '#2f9a54',
      brick: '#e07a4a', brickDark: '#9a4220', brickLight: '#f7a97e', wood: '#b9824a', woodLight: '#e3b27a', woodDark: '#7a4f24',
      stone: '#9fb8c8', stoneDark: '#6a8496', stoneLight: '#cfe2ee',
      far: '#9cc6dc', mid: '#6cc09a', near: '#3f9a72', trees: '#2f7e5a', rays: true, vignette: 0.24,
    },
  };

  var tileCache = {};
  function tilesFor(theme) {
    if (!tileCache[theme]) tileCache[theme] = themeTiles(THEMES[theme] || THEMES.meadow, theme);
    return tileCache[theme];
  }

  // ───────────────────────────── fondos con paralaje ─────────────────────────────
  // Capas de 512 px que se repiten sin costura (senos con periodos enteros). Las lejanas se funden con el
  // color del horizonte (perspectiva atmosférica).
  var LW = 512;
  function waveH(x, parts) {
    var v = 0;
    for (var i = 0; i < parts.length; i++) v += parts[i][0] * Math.sin(((x * parts[i][1]) / LW) * Math.PI * 2 + parts[i][2]);
    return v;
  }
  function layer(h, heightAt, color, rim, opts) {
    opts = opts || {};
    var c = canvas(LW, h);
    var g = c.getContext('2d');
    var r = rng(opts.seed || 3);
    for (var x = 0; x < LW; x++) {
      var top = Math.max(0, Math.round(heightAt(x)));
      g.fillStyle = color;
      g.fillRect(x, top, 1, h - top);
      if (rim) {
        g.fillStyle = rim;
        g.fillRect(x, top, 1, 1);
      }
      if (opts.shade) {
        var slope = heightAt(x + 1) - heightAt(x);
        if (slope > 0.25) {
          g.fillStyle = opts.shade;
          g.fillRect(x, top + 1, 1, Math.min(h - top, 18));
        }
      }
    }
    if (opts.trees) {
      for (var t = 0; t < opts.trees.n; t++) {
        var tx = Math.floor(r() * LW);
        var ty = Math.round(heightAt(tx));
        var rad = 3 + Math.floor(r() * 4);
        g.fillStyle = opts.trees.color;
        for (var k = -1; k <= 1; k++) {
          var cx = ((tx + k * LW) | 0);
          g.beginPath();
          g.arc(cx, ty - rad + 3, rad, 0, Math.PI * 2);
          g.fill();
          g.fillRect(cx - 1, ty - 2, 2, 6);
        }
        g.fillStyle = opts.trees.light;
        for (var k2 = -1; k2 <= 1; k2++) g.fillRect(tx + k2 * LW - rad + 2, ty - rad * 2 + 4, 2, 2);
      }
    }
    if (opts.castles) {
      opts.castles.forEach(function (cs) {
        var base = Math.round(heightAt(cs[0])) + 4;
        g.fillStyle = color;
        g.fillRect(cs[0], base - cs[1], cs[2], cs[1]);
        for (var m = 0; m < cs[2]; m += 4) g.fillRect(cs[0] + m, base - cs[1] - 3, 2, 3);
        g.fillStyle = opts.windows;
        for (var wy = base - cs[1] + 6; wy < base - 4; wy += 9) g.fillRect(cs[0] + Math.floor(cs[2] / 2) - 1, wy, 2, 3);
      });
    }
    // Color del borde inferior (para rellenar bajo la capa sin leer píxeles del canvas).
    c.bottomColor = opts.haze ? mix(color, opts.haze[0], opts.haze[1]) : color;
    if (opts.haze) {
      for (var y = 0; y < h; y++) {
        var a = Math.max(0, (y - h * 0.35) / (h * 0.65)) * opts.haze[1];
        g.fillStyle = rgba(opts.haze[0], a.toFixed(3));
        g.globalCompositeOperation = 'source-atop';
        g.fillRect(0, y, LW, 1);
        g.globalCompositeOperation = 'source-over';
      }
    }
    return c;
  }

  function cloudLayer(color, h, n, seed) {
    var c = canvas(LW, h);
    var g = c.getContext('2d');
    var r = rng(seed);
    for (var i = 0; i < n; i++) {
      var x = Math.floor(r() * LW);
      var y = 10 + Math.floor(r() * (h - 30));
      var w = 28 + Math.floor(r() * 30);
      for (var k = -1; k <= 1; k++) {
        var cx = x + k * LW;
        g.fillStyle = mix(color, '#9ab8d8', 0.25);
        g.fillRect(cx + 2, y + 9, w - 2, 3);
        g.fillStyle = color;
        g.fillRect(cx, y + 6, w, 5);
        g.fillRect(cx + 5, y + 2, Math.floor(w * 0.45), 6);
        g.fillRect(cx + Math.floor(w * 0.5), y, Math.floor(w * 0.3), 7);
        g.fillStyle = '#ffffff';
        g.fillRect(cx + 6, y + 2, Math.floor(w * 0.3), 1);
        g.fillRect(cx + Math.floor(w * 0.5) + 1, y, Math.floor(w * 0.2), 1);
      }
    }
    return c;
  }

  var backCache = {};
  function backdrop(theme) {
    if (backCache[theme]) return backCache[theme];
    var th = THEMES[theme] || THEMES.meadow;
    var b = { sky: th.sky, skyHigh: th.skyHigh, layers: [], rays: th.rays, sun: th.sun, vignette: th.vignette, dark: th.dark };
    var horizon = th.sky[1];
    if (theme === 'cave') {
      b.layers.push({ img: layer(170, function (x) { return 40 + waveH(x, [[26, 3, 0.4], [14, 7, 1.2], [8, 13, 2]]) + (x % 37 < 4 ? -30 : 0); }, th.far, mix(th.far, '#6a78c8', 0.4), { haze: [horizon, 0.5], seed: 4 }), kx: 0.15, ky: 0.12 });
      b.layers.push({ img: (function () {
        var L = layer(140, function (x) { return 50 + waveH(x, [[22, 4, 2.1], [12, 9, 0.3]]); }, th.mid, mix(th.mid, '#8a9ae8', 0.35), { seed: 9 });
        var g = L.getContext('2d');
        var r = rng(21);
        for (var i = 0; i < 26; i++) {
          var x = Math.floor(r() * LW);
          var y = 60 + Math.floor(r() * 70);
          g.fillStyle = th.crystals;
          g.fillRect(x, y, 2, 3);
          g.fillStyle = '#ffffff';
          g.fillRect(x, y, 1, 1);
        }
        return L;
      })(), kx: 0.35, ky: 0.25 });
      var ceil = layer(60, function (x) { return 60 - Math.max(0, 14 + waveH(x, [[10, 5, 0.2], [8, 11, 1.4]]) + (x % 23 < 3 ? 26 : 0) + (x % 41 < 2 ? 16 : 0)); }, '#0a0e28', '#2a3470', { seed: 2 });
      b.ceiling = canvas(ceil.width, ceil.height);
      var cg = b.ceiling.getContext('2d');
      cg.translate(0, ceil.height);
      cg.scale(1, -1);
      cg.drawImage(ceil, 0, 0);
    } else {
      var far = theme === 'tower' ? th.far : mix(th.far, horizon, 0.35);
      b.layers.push({ img: layer(180, function (x) {
        var ridge = 1 - Math.abs(Math.sin((x / LW) * Math.PI * 3 + 0.4));
        var ridge2 = 1 - Math.abs(Math.sin((x / LW) * Math.PI * 7 + 1.1));
        return 120 - ridge * 70 - ridge2 * 22;
      }, far, mix(far, '#ffffff', 0.35), { shade: mix(far, '#000000', 0.08), haze: [th.haze, 0.75], seed: 5 }), kx: 0.12, ky: 0.08 });
      if (theme === 'tower') {
        b.layers.push({ img: layer(150, function (x) { return 95 + waveH(x, [[10, 2, 0.5], [6, 5, 1.3]]); }, th.mid, mix(th.mid, '#ffd0a0', 0.4), { castles: [[40, 46, 14], [70, 30, 10], [200, 58, 16], [236, 34, 12], [330, 40, 14], [420, 64, 18], [452, 30, 10]], windows: '#ffd36a', haze: [th.haze, 0.45], seed: 6 }), kx: 0.25, ky: 0.18 });
        b.layers.push({ img: layer(110, function (x) { return 70 + waveH(x, [[12, 3, 0.9], [7, 8, 0.1]]); }, th.near, mix(th.near, '#ffb080', 0.3), { seed: 8 }), kx: 0.45, ky: 0.32 });
      } else {
        b.layers.push({ img: layer(150, function (x) { return 80 + waveH(x, [[18, 2, 0.8], [12, 5, 2.2], [5, 11, 0.4]]); }, mix(th.mid, horizon, 0.18), mix(th.mid, '#ffffff', 0.3), { trees: { n: 24, color: mix(th.trees, horizon, 0.2), light: mix(th.mid, '#ffffff', 0.25) }, haze: [th.haze, 0.35], seed: 7 }), kx: 0.3, ky: 0.18 });
        b.layers.push({ img: layer(110, function (x) { return 66 + waveH(x, [[14, 3, 1.7], [8, 7, 0.2], [4, 16, 1.1]]); }, th.near, mix(th.near, '#ffffff', 0.25), { trees: { n: 14, color: th.trees, light: mix(th.near, '#ffffff', 0.3) }, seed: 12 }), kx: 0.5, ky: 0.32 });
      }
      if (th.cloud) b.clouds = { img: cloudLayer(th.cloud, 150, 9, theme.length * 11), kx: 0.2, ky: 0.1, drift: 0.08 };
    }
    backCache[theme] = b;
    return b;
  }

  // ───────────────────────────── luces y sombras pre-renderizadas ─────────────────────────────
  function radial(size, stops) {
    var c = canvas(size, size);
    var g = c.getContext('2d');
    var gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    stops.forEach(function (s) { gr.addColorStop(s[0], s[1]); });
    g.fillStyle = gr;
    g.fillRect(0, 0, size, size);
    return c;
  }
  function glowSprite(r, g2, b) {
    return radial(64, [[0, 'rgba(' + r + ',' + g2 + ',' + b + ',0.9)'], [0.22, 'rgba(' + r + ',' + g2 + ',' + b + ',0.45)'], [0.55, 'rgba(' + r + ',' + g2 + ',' + b + ',0.12)'], [1, 'rgba(' + r + ',' + g2 + ',' + b + ',0)']]);
  }
  var shadow = (function () {
    var c = canvas(64, 16);
    var g = c.getContext('2d');
    g.translate(32, 8);
    g.scale(1, 0.25);
    var gr = g.createRadialGradient(0, 0, 0, 0, 0, 32);
    gr.addColorStop(0, 'rgba(10,8,30,0.9)');
    gr.addColorStop(0.55, 'rgba(10,8,30,0.55)');
    gr.addColorStop(1, 'rgba(10,8,30,0)');
    g.fillStyle = gr;
    g.fillRect(-32, -32, 64, 64);
    return c;
  })();
  var vignette = (function () {
    var c = canvas(170, 130);
    var g = c.getContext('2d');
    g.translate(85, 65);
    g.scale(1, 130 / 170);
    var gr = g.createRadialGradient(0, 0, 40, 0, 0, 112);
    gr.addColorStop(0, 'rgba(0,0,0,0)');
    gr.addColorStop(0.6, 'rgba(6,4,20,0.35)');
    gr.addColorStop(1, 'rgba(6,4,20,1)');
    g.fillStyle = gr;
    g.fillRect(-120, -120, 240, 240);
    return c;
  })();
  var darkness = radial(128, [[0, 'rgba(4,6,22,0)'], [0.35, 'rgba(4,6,22,0.05)'], [0.75, 'rgba(4,6,22,0.45)'], [1, 'rgba(4,6,22,0.62)']]);
  var rays = (function () {
    var c = canvas(170, 130);
    var g = c.getContext('2d');
    [[20, 26, 0.5], [62, 18, 0.35], [96, 30, 0.45], [140, 16, 0.3]].forEach(function (rb) {
      var gr = g.createLinearGradient(0, 0, 0, 130);
      gr.addColorStop(0, 'rgba(255,250,220,' + rb[2] + ')');
      gr.addColorStop(1, 'rgba(255,250,220,0)');
      g.fillStyle = gr;
      g.beginPath();
      g.moveTo(rb[0] + 40, 0);
      g.lineTo(rb[0] + 40 + rb[1], 0);
      g.lineTo(rb[0] - 20 + rb[1] * 1.8, 130);
      g.lineTo(rb[0] - 20, 130);
      g.closePath();
      g.fill();
    });
    return c;
  })();
  var sparkle = paint(['...W...', '...W...', '..WYW..', 'WWYWYWW', '..WYW..', '...W...', '...W...'], { W: '#ffffff', Y: '#fff1a0' });
  var puff = paint(['..aaaa..', '.abbbba.', 'abbbbbba', 'abbbbbba', 'abbbbbba', 'aabbbbaa', '.aaaaaa.', '..aaaa..'], { a: 'rgba(225,220,205,0.75)', b: 'rgba(255,253,245,0.95)' });
  var STAR = ['....k....', '...kYk...', '...kYk...', 'kkkkYWkkk', 'kYYYWYYYk', '.kYYYYYk.', '..kYYYk..', '.kYYkYYk.', '.kYk.kYk.', '.kk...kk.'];
  var star = paint(STAR, { k: '#5e3a08', Y: '#ffd43a', W: '#fff6c2' });
  var starOff = paint(STAR, { k: '#2a2d44', Y: '#5a5f7a', W: '#767b96' });
  var bubble = paint(['.ww.', 'w..w', 'w.Ww', '.ww.'], { w: 'rgba(220,245,255,0.9)', W: '#ffffff' });

  // ───────────────────────────── decoración ─────────────────────────────
  var DECO_M = {
    G: { r: ['#256b24', '#3fa33a', '#8fd94a'] }, F: { r: ['#5e3b1d', '#8a5a32', '#b9824a'] }, f: { r: ['#5e3b1d', '#8a5a32', '#b9824a'], t: 0 },
    B: { c: '#e8402f' }, Y: { c: '#ffd43a' },
  };
  function bush() {
    var G = new Grid(32, 12);
    G.ellipse(8, 8, 8, 6, 'G').ellipse(17, 6, 7, 6.5, 'G').ellipse(26, 8, 6, 5, 'G');
    G.rect(1, 8, 30, 4, 'G');
    G.set(6, 5, 'B').set(18, 3, 'Y').set(25, 6, 'B').set(12, 8, 'Y');
    return finish(G, DECO_M, '#123d1a');
  }
  function fence() {
    var G = new Grid(16, 12);
    G.rect(2, 0, 2, 12, 'F').rect(10, 0, 2, 12, 'F');
    G.rect(0, 3, 16, 2, 'F').rect(0, 8, 16, 2, 'F');
    G.set(2, 0, null).set(10, 0, null);
    return finish(G, DECO_M, '#3a2414');
  }
  var FLAG_M = { G: { r: ['#256b24', '#3fa33a', '#8fd94a'] }, W: { c: '#ffffff' }, Y: { c: '#ffd43a' } };
  function flagFrame(f) {
    var G = new Grid(16, 11);
    for (var x = 0; x < 15; x++) {
      var off = Math.round(Math.sin(x * 0.55 - f * 2.1) * 1.2 * (x / 14));
      var len = 10 - Math.floor(x / 3);
      for (var y = 0; y < len; y++) G.set(x, Math.floor((10 - len) / 2) + y + off, 'G');
    }
    var cy = 5 + Math.round(Math.sin(5 * 0.55 - f * 2.1) * 0.6);
    G.ellipse(6, cy, 2.6, 2.4, 'W');
    G.set(6, cy - 1, 'Y').set(5, cy, 'Y').set(6, cy, 'Y').set(7, cy, 'Y').set(6, cy + 1, 'Y');
    return finish(G, FLAG_M, '#1b1d2e');
  }

  var BLOB_FRAMES = [blobFrame(7, 5.2, 0), blobFrame(7.5, 4.6, 1), blobFrame(7, 5.2, 0), blobFrame(6.5, 5.8, -1)];

  window.SRBArt = {
    T: T,
    mix: mix,
    ruy: makeRuy(false),
    ruyFire: makeRuy(true),
    blob: BLOB_FRAMES.map(function (G) { return pair(finish(G, BLOB_M, '#22142e')); }),
    blobFlat: pair(finish(blobFrame(8, 2.4, 0, true), BLOB_M, '#22142e')),
    bee: [0, 1, 2, 1].map(function (w) { return pair(finish(beeFrame(w), BEE_M, '#1d1a12')); }),
    hog: [0, 1, 2, 3].map(function (s) { return pair(finish(hogFrame(s), HOG_M, '#24170c')); }),
    mushroom: finish(mushroom(), ITEM_M, '#2a1a12'),
    flower: [0, 1, 0, -1].map(function (s) { return finish(flower(s), ITEM_M, '#2a1a12'); }),
    coin: [5, 4, 2.5, 1, 2.5, 4].map(function (rx) { return finish(coinFrame(rx), COIN_M, '#5e3a08'); }),
    fireball: [0, 1, 2, 3].map(function (f) { return finish(fireFrame(f), FIRE_M, '#6a1a08'); }),
    bush: bush(),
    fence: fence(),
    flag: [0, 1, 2].map(flagFrame),
    glow: { warm: glowSprite(255, 210, 90), fire: glowSprite(255, 120, 40), white: glowSprite(235, 245, 255), green: glowSprite(140, 255, 120), cyan: glowSprite(120, 230, 255) },
    shadow: shadow,
    vignette: vignette,
    darkness: darkness,
    rays: rays,
    sparkle: sparkle,
    puff: puff,
    bubble: bubble,
    star: star,
    starOff: starOff,
    themes: THEMES,
    tiles: tilesFor,
    backdrop: backdrop,
  };
})();
