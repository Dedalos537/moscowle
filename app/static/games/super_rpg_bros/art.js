/*
 * Super RPG Bros. — arte en píxeles.
 *
 * Cada sprite es una matriz de caracteres indexada a una paleta corta (como un PNG indexado): se pinta una sola vez
 * en un canvas pequeño y después solo se copia. Paleta saturada y limpia, contorno oscuro para siluetas claras.
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

  /** rows: array de strings del mismo largo; pal: { char: '#rrggbb' }; '.' es transparente. */
  function paint(rows, pal, flip) {
    var h = rows.length;
    var w = rows[0].length;
    var c = canvas(w, h);
    var g = c.getContext('2d');
    for (var y = 0; y < h; y++) {
      for (var x = 0; x < w; x++) {
        var ch = rows[y][flip ? w - 1 - x : x];
        if (ch === '.' || ch === ' ' || !pal[ch]) continue;
        g.fillStyle = pal[ch];
        g.fillRect(x, y, 1, 1);
      }
    }
    return c;
  }

  function pair(rows, pal) {
    return { r: paint(rows, pal, false), l: paint(rows, pal, true) };
  }

  // ───────────────────────────── Ruy (jugador) ─────────────────────────────
  // Gorra verde con visera, polerón naranja, pantalón azul, zapatillas blancas.
  var RUY = {
    k: '#1b1d2e', G: '#3fa33a', L: '#8fd94a', D: '#256b24', S: '#f4bf93', s: '#d9946a',
    W: '#ffffff', P: '#1b1d2e', O: '#f08a24', A: '#c45f12', N: '#2c4fb8', n: '#1f377f', w: '#f3f3f3', K: '#5a3a24',
  };
  var RUY_FIRE = Object.assign({}, RUY, { G: '#e8402f', L: '#ff9a8a', D: '#a4241a', O: '#fdfdfd', A: '#d6d6d6', N: '#e8402f', n: '#a4241a' });

  var HEAD = [
    '.....kkkkkk.....',
    '...kkGGGGGGkk...',
    '..kGGLLGGGGGGkkk',
    '..kGLGGGGGGGGGGk',
    '..kDDDDDDDDDkkk.',
    '..kSSSSSSSSSSk..',
    '.kSSWWkSSWWkSSk.',
    '.kSSWPkSSWPkSSk.',
    '..kSSSSssSSSSk..',
    '...kSSSkkSSSk...',
  ];
  var SMALL_BODY = {
    idle: ['..kkOOOOOOOkk...', '.kSOOAOOOAOOSk..', '.kSkOOOOOOOkSk..', '...kNNNkNNNk....', '...kwwwkwwwk....', '..kKKKk.kKKKk...'],
    run1: ['..kkOOOOOOOkk...', '..kOOAOOOAOOSk..', '..kSOOOOOOOkk...', '..kNNNk.kNNk....', '.kwwwk...kwwk...', 'kKKKk.....kKKk..'],
    run2: ['..kkOOOOOOOkk...', '..kSOAOOOAOOk...', '...kOOOOOOOk....', '....kNNNNNk.....', '....kwwwwwk.....', '...kKKKkKKKk....'],
    run3: ['..kkOOOOOOOkk...', '.kSOOAOOOAOOk...', '..kkOOOOOOOSk...', '...kNNk.kNNNk...', '...kwwk...kwwwk.', '..kKKk.....kKKKk'],
    jump: ['kSkkOOOOOOOkkSk.', '.kkOOAOOOAOOkk..', '...kOOOOOOOk....', '..kNNNk.kNNNk...', '.kwwwk...kwwwk..', '.kKKk.....kKKk..'],
    skid: ['..kkOOOOOOOkk...', '.kOOOAOOOAOOSk..', '..kOOOOOOOOkSk..', '...kNNNkNNNk....', '..kwwwk.kwwwk...', '.kKKKk...kKKKk..'],
    crouch: ['................', '................', '..kkOOOOOOOkk...', '.kSOONNNNNOOSk..', '..kwwwkkkwwwk...', '.kKKKk...kKKKk..'],
  };

  function bigBody(small) {
    // Cuerpo alto: torso más largo y piernas más largas a partir del cuerpo pequeño.
    var torso = small.slice(0, 3);
    var legs = small.slice(3);
    var midTorso = ['.kOOOOOOOOOOOk..', '.kOOOOAOAOOOOk..', '.kOOOOOOOOOOOk..', '..kOOOOOOOOOk...'];
    var thighs = [legs[0], legs[0].replace(/w/g, 'N'), legs[0].replace(/w/g, 'N')];
    return torso.concat(midTorso, ['..knnnnnnnnnk...'], thighs, legs.slice(0), ['................']);
  }

  function makeRuy(pal) {
    var small = {};
    var big = {};
    Object.keys(SMALL_BODY).forEach(function (k) {
      small[k] = pair(HEAD.concat(SMALL_BODY[k]), pal);
      var head = HEAD;
      var body = k === 'crouch' ? SMALL_BODY.crouch : bigBody(SMALL_BODY[k]);
      var rows = head.concat(body);
      while (rows.length < 32) rows.unshift('................');
      big[k] = pair(rows.slice(rows.length - 32), pal);
    });
    return { small: small, big: big };
  }

  // ───────────────────────────── enemigos ─────────────────────────────
  var BLOB = { k: '#22142e', V: '#8a4fd8', v: '#5f2fa6', l: '#c39bf2', W: '#ffffff', P: '#22142e', T: '#f2c94c' };
  var BLOB_A = [
    '................', '................', '.....kkkkkk.....', '...kkVVVVVVkk...', '..kVVlVVVVVVVk..', '.kVVlVVVVVVVVVk.',
    '.kVVWWkVVkWWVVk.', 'kVVVWPkVVkPWVVVk', 'kVVVVVVVVVVVVVVk', 'kVVVVVkkkkVVVVVk', 'kvVVVVVVVVVVVVvk', '.kvVVVVVVVVVVvk..',
    '..kkvvvvvvvvkk..', '...kkkkkkkkkk...', '..kTTk....kTTk..', '................',
  ];
  var BLOB_B = BLOB_A.slice(0, 14).concat(['...kTTk..kTTk...', '................']);
  var BLOB_FLAT = [
    '................', '................', '................', '................', '................', '................',
    '................', '................', '................', '................', '...kkkkkkkkkk...', '.kkVVVVVVVVVVkk.',
    'kVVWWkVVVVkWWVVk', 'kvVVVVVVVVVVVVvk', '.kkvvvvvvvvvvkk.', '................',
  ];

  var BEE = { k: '#1d1a12', Y: '#f6c431', y: '#c99212', B: '#1d1a12', W: '#e9f6ff', w: '#a9d8f2', P: '#1d1a12', R: '#ffffff' };
  var BEE_A = [
    '................', '....ww....ww....', '...wWWw..wWWw...', '...wWWWwwWWWw...', '....wwkkkkww....', '...kkYYYYYYkk...',
    '..kYYkYYkYYYYk..', '.kYRPkYYkYRPYYk.', '.kYYYkYYkYYYYYk.', '.kYYYkYYkYYYYk..', '..kyyykyyykyyk..', '...kkkkkkkkkk...',
    '.......kk.......', '................', '................', '................',
  ];
  var BEE_B = ['................', '................', '....ww....ww....', '...wWWwwwWWWw...'].concat(BEE_A.slice(4));

  var HOG = { k: '#24170c', M: '#8a5a32', m: '#5e3b1d', S: '#c9c9d6', s: '#8d8da0', F: '#f1c79a', W: '#ffffff', P: '#24170c', N: '#e2574c' };
  var HOG_A = [
    '................', '................', '....s.s.s.s.....', '...sSsSsSsSs....', '..sSSSSSSSSSs...', '.sSSmMMMMMMSSs..',
    '.sSmMMMMMMMMSk..', 'sSmMMMMMMMMFFFk.', 'sSmMMMMMMMFWPFk.', 'sSmMMMMMMMFFFFNk', '.kmMMMMMMMMFFFk..', '..kmmmmmmmmmkk...',
    '...kFFk..kFFk...', '...kkk....kkk...', '................', '................',
  ];
  var HOG_B = HOG_A.slice(0, 12).concat(['..kFFk....kFFk..', '..kkk......kkk..', '................', '................']);

  // ───────────────────────────── objetos ─────────────────────────────
  var ITEM = { k: '#2a1a12', R: '#e8402f', r: '#a4241a', W: '#ffffff', S: '#f4dcb5', s: '#d8b98a', G: '#3fa33a', g: '#256b24', Y: '#ffd43a', O: '#f08a24', P: '#2a1a12' };
  var MUSH = [
    '................', '.....kkkkkk.....', '...kkRRWWRRkk...', '..kRRRWWWWRRRk..', '.kRWWRRWWRRWWRk.', '.kWWWRRRRRRWWWk.',
    'kRWWRRRRRRRRWWRk', 'kRRRRRRRRRRRRRRk', 'kkkkkkkkkkkkkkkk', '..kSSSWSSWSSSk..', '..kSSSPSSPSSSk..', '..kSSSSSSSSSSk..',
    '...ksSSSSSSsk...', '....kkkkkkkk....', '................', '................',
  ];
  var FLOWER = [
    '................', '.....kkkkkk.....', '...kkOOOOOOkk...', '..kOOYYYYYYOOk..', '.kOYYWWkkWWYYOk.', '.kOYYWPkkWPYYOk.',
    '..kOOYYYYYYOOk..', '...kkOOOOOOkk...', '.....kkGGkk.....', '..kk...kGk..kk..', '.kGGk..kGk.kGGk.', '.kGGGk.kGk.kGGGk',
    '..kGGGkkGkkGGGk.', '...kkGGGGGGGkk..', '.....kkkkkkk....', '................',
  ];
  var COIN = { k: '#5e3a08', Y: '#ffd43a', y: '#e0a91c', W: '#fff6c2' };
  var COIN_FRAMES = [
    ['....kkkkkk....', '...kYYYYYYk...', '..kYWWYYYYyk..', '..kYWYYyYYyk..', '..kYWYYyYYyk..', '..kYYYYyYYyk..', '..kYYYYyYYyk..', '..kYYYYyYYyk..', '..kYYYYYYYyk..', '...kyyyyyyk...', '....kkkkkk....'],
    ['.....kkkk.....', '....kYYYYk....', '....kWYYyk....', '....kWYyyk....', '....kWYyyk....', '....kYYyyk....', '....kYYyyk....', '....kYYyyk....', '....kYYYyk....', '....kyyyyk....', '.....kkkk.....'],
    ['......kk......', '......kk......', '.....kWYk.....', '.....kYyk.....', '.....kYyk.....', '.....kYyk.....', '.....kYyk.....', '.....kYyk.....', '.....kYyk.....', '......kk......', '......kk......'],
  ];
  var FIRE = { R: '#ff5a1f', Y: '#ffd43a', W: '#fff6c2' };
  var FIREBALL = ['..RRRR..', '.RYYYYR.', 'RYYWWYYR', 'RYWWWWYR', 'RYWWWWYR', 'RYYWWYYR', '.RYYYYR.', '..RRRR..'];

  // ───────────────────────────── tiles ─────────────────────────────
  function tile(draw) {
    var c = canvas(T, T);
    draw(c.getContext('2d'));
    return c;
  }
  function rect(g, color, x, y, w, h) {
    g.fillStyle = color;
    g.fillRect(x, y, w, h);
  }

  function themeTiles(th) {
    var t = {};
    t.ground = tile(function (g) {
      rect(g, th.dirt, 0, 0, T, T);
      rect(g, th.dirtDark, 0, 15, T, 1);
      [[3, 4], [10, 2], [6, 9], [12, 11], [2, 13]].forEach(function (p) { rect(g, th.dirtDark, p[0], p[1], 2, 2); });
      [[5, 6], [13, 7], [1, 9]].forEach(function (p) { rect(g, th.dirtLight, p[0], p[1], 1, 1); });
    });
    t.top = tile(function (g) {
      g.drawImage(t.ground, 0, 0);
      rect(g, th.grass, 0, 0, T, 5);
      rect(g, th.grassLight, 0, 0, T, 1);
      rect(g, th.grassDark, 0, 5, T, 1);
      [1, 5, 9, 13].forEach(function (x) { rect(g, th.grass, x, 5, 2, 2); });
    });
    t.brick = tile(function (g) {
      rect(g, th.brick, 0, 0, T, T);
      rect(g, th.brickDark, 0, 7, T, 1);
      rect(g, th.brickDark, 0, 15, T, 1);
      rect(g, th.brickDark, 7, 0, 1, 7);
      rect(g, th.brickDark, 3, 8, 1, 7);
      rect(g, th.brickDark, 11, 8, 1, 7);
      rect(g, th.brickLight, 0, 0, T, 1);
      rect(g, th.brickLight, 0, 8, 3, 1);
    });
    t.used = tile(function (g) {
      rect(g, '#1b1d2e', 0, 0, T, T);
      rect(g, '#b07a3c', 1, 1, 14, 14);
      rect(g, '#8a5a24', 1, 14, 14, 1);
      rect(g, '#8a5a24', 14, 1, 1, 14);
      [[3, 3], [12, 3], [3, 12], [12, 12]].forEach(function (p) { rect(g, '#1b1d2e', p[0], p[1], 1, 1); });
    });
    t.question = [0, 1, 2].map(function (shine) {
      return tile(function (g) {
        rect(g, '#1b1d2e', 0, 0, T, T);
        rect(g, ['#ffb92e', '#ffcc4d', '#ffe07a'][shine], 1, 1, 14, 14);
        rect(g, '#c97a12', 1, 14, 14, 1);
        rect(g, '#c97a12', 14, 1, 1, 14);
        [[3, 3], [12, 3], [3, 12], [12, 12]].forEach(function (p) { rect(g, '#1b1d2e', p[0], p[1], 1, 1); });
        // Signo «?»
        rect(g, '#7a3f05', 6, 4, 4, 1);
        rect(g, '#7a3f05', 5, 5, 2, 2);
        rect(g, '#7a3f05', 9, 5, 2, 3);
        rect(g, '#7a3f05', 7, 8, 3, 1);
        rect(g, '#7a3f05', 7, 9, 2, 2);
        rect(g, '#7a3f05', 7, 12, 2, 1);
      });
    });
    t.platform = tile(function (g) {
      rect(g, th.wood, 0, 0, T, 5);
      rect(g, th.woodLight, 0, 0, T, 1);
      rect(g, th.woodDark, 0, 4, T, 1);
      [4, 12].forEach(function (x) { rect(g, th.woodDark, x, 1, 1, 3); });
    });
    var pipe = function (left, top) {
      return tile(function (g) {
        var x0 = top ? 0 : left ? 1 : 0;
        var w = top ? T : 15;
        rect(g, '#1b1d2e', x0, 0, w, T);
        rect(g, '#3fa33a', x0 + (left ? 1 : 0), top ? 1 : 0, w - 1, top ? 14 : T);
        rect(g, '#8fd94a', left ? x0 + 3 : x0 + 1, top ? 2 : 0, 2, top ? 12 : T);
        rect(g, '#256b24', left ? x0 + w - 4 : x0 + w - 5, top ? 2 : 0, 3, top ? 12 : T);
        if (!left) rect(g, '#1b1d2e', T - 1, 0, 1, T);
        if (left) rect(g, '#1b1d2e', 0, 0, 1, T);
      });
    };
    t.pipeTL = pipe(true, true);
    t.pipeTR = pipe(false, true);
    t.pipeL = pipe(true, false);
    t.pipeR = pipe(false, false);
    t.spikes = tile(function (g) {
      for (var i = 0; i < 4; i++) {
        for (var y = 0; y < 8; y++) rect(g, y < 2 ? '#f1f1f6' : '#a8a8bc', i * 4 + Math.floor(y / 4), 8 + y, 4 - Math.floor(y / 2), 1);
      }
      rect(g, '#5d5d72', 0, 15, T, 1);
    });
    t.water = [0, 1, 2, 3].map(function (f) {
      return tile(function (g) {
        rect(g, 'rgba(46,140,230,0.72)', 0, 0, T, T);
        for (var x = 0; x < T; x++) {
          var y = Math.round(1.5 + Math.sin((x + f * 4) * 0.4) * 1.5);
          rect(g, 'rgba(210,240,255,0.9)', x, y, 1, 1);
        }
        rect(g, 'rgba(120,200,255,0.35)', (f * 5) % 12, 8, 4, 1);
      });
    });
    t.waterDeep = tile(function (g) {
      rect(g, 'rgba(30,110,205,0.78)', 0, 0, T, T);
    });
    t.stone = tile(function (g) {
      rect(g, th.stone, 0, 0, T, T);
      rect(g, th.stoneDark, 0, 15, T, 1);
      rect(g, th.stoneDark, 15, 0, 1, T);
      rect(g, th.stoneLight, 0, 0, T, 1);
      rect(g, th.stoneLight, 0, 0, 1, T);
      rect(g, th.stoneDark, 5, 6, 3, 2);
    });
    return t;
  }

  var THEMES = {
    meadow: {
      sky: ['#5ec8ff', '#a8e6ff'], hillFar: '#7ccf8a', hillNear: '#4fae5c', hillDot: '#3a8f48', cloud: '#ffffff',
      dirt: '#c8834a', dirtDark: '#9a5a2c', dirtLight: '#e2a46e', grass: '#5cc33f', grassLight: '#a2ee6e', grassDark: '#3a8f2a',
      brick: '#d8693a', brickDark: '#8f3a18', brickLight: '#f39a6a', wood: '#b9824a', woodLight: '#e3b27a', woodDark: '#7a4f24',
      stone: '#9aa0b8', stoneDark: '#666b85', stoneLight: '#c8cde0',
    },
    cave: {
      sky: ['#141a3a', '#2a2f5e'], hillFar: '#1e2552', hillNear: '#262f66', hillDot: '#34407e', cloud: null,
      dirt: '#5d6aa8', dirtDark: '#3c4680', dirtLight: '#8590cc', grass: '#4fb2c9', grassLight: '#a4eaf5', grassDark: '#2f7c90',
      brick: '#4a66c9', brickDark: '#25357a', brickLight: '#8aa2f2', wood: '#9a7a5a', woodLight: '#c9a57e', woodDark: '#5e4428',
      stone: '#6e76a8', stoneDark: '#454c7a', stoneLight: '#a2aad6',
    },
    tower: {
      sky: ['#ff9a5c', '#ffd88a'], hillFar: '#e98b6a', hillNear: '#c96a52', hillDot: '#a8513f', cloud: '#fff2df',
      dirt: '#a88466', dirtDark: '#7a5c44', dirtLight: '#c9a688', grass: '#7cc35a', grassLight: '#b8ec8a', grassDark: '#4f8f36',
      brick: '#b9715a', brickDark: '#7a3f2c', brickLight: '#e0a088', wood: '#a46a3a', woodLight: '#d89a62', woodDark: '#6a4020',
      stone: '#c2b4a4', stoneDark: '#8f8070', stoneLight: '#e4d8ca',
    },
    lake: {
      sky: ['#4fb6e8', '#d6f2ff'], hillFar: '#88d0b8', hillNear: '#56b08e', hillDot: '#3c8a6c', cloud: '#ffffff',
      dirt: '#d9b27a', dirtDark: '#a8824e', dirtLight: '#f2d39e', grass: '#4fcf7a', grassLight: '#9ff2b6', grassDark: '#2f9a54',
      brick: '#e07a4a', brickDark: '#9a4220', brickLight: '#f7a97e', wood: '#b9824a', woodLight: '#e3b27a', woodDark: '#7a4f24',
      stone: '#9fb8c8', stoneDark: '#6a8496', stoneLight: '#cfe2ee',
    },
  };

  var tileCache = {};
  function tilesFor(theme) {
    if (!tileCache[theme]) tileCache[theme] = themeTiles(THEMES[theme] || THEMES.meadow);
    return tileCache[theme];
  }

  // Decoración delantera (capa 3) y del fondo.
  var DECO = { k: '#1b3d1a', G: '#3fa33a', L: '#8fd94a', D: '#256b24', F: '#8a5a32', f: '#5e3b1d', W: '#ffffff', R: '#e8402f', Y: '#ffd43a' };
  var BUSH = [
    '................................', '................................', '...........kkkkk................', '.........kkGGGGGkk......kkkk....',
    '........kGGLLGGGGGk...kkGGGGkk..', '.......kGGLGGGGGGGGk.kGGLLGGGGk.', '.....kkGGGGGGGGGGGGGkGLGGGGGGGGk', '...kkGGGLLGGGGGGGGDGGGGGGGGGGDGk',
    '..kGGGLGGGGGGGGGDGGGGGGGGGGGDDGk', '.kGGGGGGGGGGGDDGGGGGGGGGGGDDGGGk', 'kGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGk', 'kDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDk',
  ];
  var FENCE = [
    '..k......k......', '.kFk....kFk.....', '.kFkkkkkkFkkkkkk', '.kFFFFFFFFFFFFFF', '.kFkkkkkkFkkkkkk', '.kFk....kFk.....',
    '.kFkkkkkkFkkkkkk', '.kFFFFFFFFFFFFFF', '.kFkkkkkkFkkkkkk', '.kFk....kFk.....', '.kfk....kfk.....', '.kfk....kfk.....',
  ];
  var FLAG = { k: '#1b1d2e', G: '#3fa33a', L: '#8fd94a', W: '#ffffff', P: '#d9d9e6' };
  var FLAG_CLOTH = [
    'kkkkkkkkkkkkk...', 'kGGGGGGGGGGGGk..', 'kGGLLGGGGGGGGGk.', 'kGLGGWWWWGGGGGGk', 'kGGGWWkkWWGGGGGk', 'kGGGWkkkkWGGGGk.',
    'kGGGGWWWWGGGGk..', 'kGGGGGGGGGGGk...', 'kkkkkkkkkkkk....',
  ];

  window.SRBArt = {
    T: T,
    ruy: makeRuy(RUY),
    ruyFire: makeRuy(RUY_FIRE),
    blob: [pair(BLOB_A, BLOB), pair(BLOB_B, BLOB)],
    blobFlat: paint(BLOB_FLAT, BLOB),
    bee: [pair(BEE_A, BEE), pair(BEE_B, BEE)],
    hog: [pair(HOG_A, HOG), pair(HOG_B, HOG)],
    mushroom: paint(MUSH, ITEM),
    flower: paint(FLOWER, ITEM),
    coin: COIN_FRAMES.map(function (f) { return paint(f, COIN); }),
    fireball: paint(FIREBALL, FIRE),
    bush: paint(BUSH, DECO),
    fence: paint(FENCE, DECO),
    flag: paint(FLAG_CLOTH, FLAG),
    themes: THEMES,
    tiles: tilesFor,
  };
})();
