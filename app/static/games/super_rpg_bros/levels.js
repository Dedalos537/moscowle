/*
 * Super RPG Bros. — niveles.
 *
 * Cada nivel se arma con un constructor (suelo, huecos, bloques, tuberías…) en vez de un mapa ASCII escrito a mano:
 * así las medidas cuadran y es fácil retocar. Celdas del mapa:
 *   #  suelo (se dibuja con césped si no hay nada encima)   S  piedra      B  ladrillo     ?  bloque con moneda
 *   M  bloque con poder (champiñón / flor)                  H  bloque oculto con moneda    U  bloque usado
 *   =  plataforma de un sentido (se atraviesa desde abajo)  ^  pinchos     ~  agua (superficie)   w  agua profunda
 *   [ ] boca de tubería   { } cuerpo de tubería             o  moneda suelta
 */
(function () {
  'use strict';

  function Level(id, name, theme, w, h) {
    this.id = id;
    this.name = name;
    this.theme = theme;
    this.w = w;
    this.h = h;
    this.grid = [];
    for (var y = 0; y < h; y++) this.grid.push(new Array(w).fill(' '));
    this.enemies = [];
    this.deco = [];
    this.warps = [];
    this.rooms = {};
    this.start = { x: 2, y: h - 5 };
    this.flagX = null;
    this.time = 300;
  }

  Level.prototype.set = function (x, y, ch) {
    if (x >= 0 && y >= 0 && x < this.w && y < this.h) this.grid[y][x] = ch;
    return this;
  };
  Level.prototype.fill = function (x0, x1, y0, y1, ch) {
    for (var y = y0; y <= y1; y++) for (var x = x0; x <= x1; x++) this.set(x, y, ch);
    return this;
  };
  Level.prototype.ground = function (x0, x1, top) {
    return this.fill(x0, x1, top, this.h - 1, '#');
  };
  Level.prototype.row = function (x, y, str) {
    for (var i = 0; i < str.length; i++) if (str[i] !== '.') this.set(x + i, y, str[i]);
    return this;
  };
  Level.prototype.coins = function (x, y, n, dy) {
    for (var i = 0; i < n; i++) this.set(x + i, y + (dy ? dy(i) : 0), 'o');
    return this;
  };
  /** Tubería de 2 de ancho desde `top` hasta el suelo. `warp`: { to: 'sala', x, y } entra pulsando abajo. */
  Level.prototype.pipe = function (x, top, warp) {
    this.set(x, top, '[').set(x + 1, top, ']');
    for (var y = top + 1; y < this.h && this.grid[y][x] !== '#'; y++) this.set(x, y, '{').set(x + 1, y, '}');
    if (warp) this.warps.push({ x: x, y: top, to: warp.to, tx: warp.x, ty: warp.y });
    return this;
  };
  Level.prototype.stairs = function (x, top, steps, down) {
    for (var i = 0; i < steps; i++) {
      var hgt = down ? steps - i : i + 1;
      this.fill(x + i, x + i, top - hgt + 1, top, 'S');
    }
    return this;
  };
  Level.prototype.enemy = function (type, x, y) {
    this.enemies.push({ type: type, x: x, y: y });
    return this;
  };
  Level.prototype.bush = function (x, y) {
    this.deco.push({ kind: 'bush', x: x, y: y });
    return this;
  };
  /** Letrero de la primera vez (icono: move, jump, coin, down). */
  Level.prototype.sign = function (x, y, icon) {
    this.deco.push({ kind: 'sign', x: x, y: y, icon: icon });
    return this;
  };
  Level.prototype.fence = function (x, y, n) {
    for (var i = 0; i < n; i++) this.deco.push({ kind: 'fence', x: x + i, y: y });
    return this;
  };
  Level.prototype.flag = function (x, groundTop) {
    this.flagX = x;
    this.flagTop = groundTop - 10;
    return this;
  };

  /** Monedas que se pueden conseguir en el nivel y sus salas (para el indicador «objetos recogidos»). */
  Level.prototype.coinTotal = function () {
    var count = function (lv) {
      var n = 0;
      lv.grid.forEach(function (r) { r.forEach(function (c) { if (c === 'o' || c === '?' || c === 'H') n++; }); });
      return n;
    };
    var total = count(this);
    for (var k in this.rooms) total += count(this.rooms[k]);
    return total;
  };

  /**
   * Sala secreta: suelo, una fila de ladrillos (fila 18, cols 4-22) y una plataforma de madera (fila 14, cols 4-26).
   * Las tres filas de monedas quedan alcanzables: la 1.ª sobre la madera (fila 12), la 2.ª sobre los ladrillos
   * (fila 16) y la 3.ª a ras de suelo (fila 20). coinsRows: [[x, n], …].
   */
  function secretRoom(theme, coinsRows, exitTo) {
    var r = new Level('room', 'Sala secreta', theme, 34, 26);
    r.fill(0, 33, 0, 1, 'S').fill(0, 1, 0, 25, 'S').fill(32, 33, 0, 25, 'S').ground(2, 31, 22);
    r.start = { x: 4, y: 20 };
    r.row(4, 18, 'BBBBBBBBBBBBBBBBBBB');
    r.row(4, 14, '=======================');
    var rows = [[12, 4, 26], [16, 4, 22], [20, 3, 27]];
    coinsRows.forEach(function (row, i) {
      var lim = rows[i];
      var x = Math.max(lim[1], row[0]);
      var n = Math.min(row[1], lim[2] - x + 1);
      r.coins(x, lim[0], n);
    });
    r.pipe(28, 20, exitTo);
    r.time = null;
    r.isRoom = true;
    return r;
  }

  // ───────────────────────── 1-1 Pradera (tutorial horizontal) ─────────────────────────
  function level1() {
    var L = new Level('1-1', 'Pradera', 'meadow', 212, 26);
    L.start = { x: 3, y: 20 };
    L.ground(0, 45, 22).ground(49, 95, 22).ground(100, 150, 22).ground(154, 211, 22);
    L.row(12, 18, '?').row(18, 18, 'B?M?B').row(20, 14, '?');
    L.coins(23, 15, 4);
    L.pipe(30, 20).pipe(40, 19, { to: 'r1', x: 4, y: 20 });
    L.enemy('blob', 25, 21).enemy('blob', 36, 21).enemy('blob', 60, 21).enemy('blob', 62, 21);
    L.coins(45, 18, 5, function (i) { return -[0, 1, 2, 1, 0][i]; });
    L.row(55, 17, '======').coins(55, 15, 6);
    L.row(66, 18, 'B?B').row(70, 18, 'H').row(78, 14, 'BB?BBBBB').row(80, 18, 'M');
    L.enemy('blob', 85, 21).enemy('blob', 88, 21);
    L.coins(96, 18, 4, function (i) { return -[0, 1, 1, 0][i]; });
    L.pipe(106, 20).pipe(116, 19).pipe(126, 18);
    L.enemy('blob', 110, 21).enemy('blob', 112, 21).enemy('blob', 120, 21).enemy('blob', 132, 21);
    L.row(136, 18, '?B?B?').enemy('bee', 142, 16);
    L.coins(151, 17, 3);
    L.stairs(170, 21, 6).stairs(180, 21, 6, true);
    L.stairs(190, 21, 8);
    L.flag(203, 22);
    [5, 33, 58, 92, 118, 160, 198].forEach(function (x) { L.bush(x, 22); });
    L.fence(140, 22, 6);
    L.sign(6, 22, 'move').sign(9, 22, 'jump').sign(15, 22, 'coin').sign(37, 22, 'down');
    L.rooms.r1 = secretRoom('cave', [[6, 13], [8, 9], [10, 5]], { to: 'main', x: 44, y: 20 });
    L.time = 300;
    return L;
  }

  // ───────────────────────── 1-2 Cueva (techo, agua, plataformas) ─────────────────────────
  function level2() {
    var L = new Level('1-2', 'Cueva', 'cave', 206, 26);
    L.start = { x: 3, y: 20 };
    L.fill(0, 205, 0, 2, 'B');
    L.ground(0, 40, 22).ground(44, 80, 22).ground(84, 118, 22).ground(142, 205, 22);
    L.row(10, 17, 'B?B?B').row(14, 13, 'M');
    L.enemy('blob', 20, 21).enemy('blob', 30, 21).enemy('bee', 36, 15);
    L.row(41, 18, '===');
    L.row(50, 15, 'BBBBBBB').coins(51, 13, 5).row(52, 15, 'H');
    // Columnas de ladrillo con un tablón entre ellas: cada salto queda a 3 filas o menos (también para Ruy grande).
    L.fill(58, 59, 18, 21, 'B').row(62, 17, '==').fill(66, 67, 14, 21, 'B').coins(63, 10, 2);
    L.enemy('blob', 62, 21).enemy('blob', 72, 21).enemy('bee', 76, 14);
    L.row(81, 18, '===');
    L.pipe(92, 19, { to: 'r1', x: 4, y: 20 }).pipe(100, 18);
    L.enemy('hog', 96, 21).enemy('blob', 108, 21);
    // Laguna subterránea: superficie y fondo, con plataformas para cruzar.
    L.fill(119, 141, 20, 20, '~').fill(119, 141, 21, 24, 'w').fill(119, 141, 25, 25, 'S');
    L.row(122, 17, '====').row(130, 15, '====').row(137, 17, '===');
    L.coins(123, 15, 3).coins(131, 13, 3);
    L.row(150, 17, '?M?').enemy('hog', 158, 21).enemy('bee', 165, 14).enemy('blob', 170, 21);
    L.stairs(180, 21, 7);
    L.flag(196, 22);
    L.rooms.r1 = secretRoom('cave', [[6, 15], [6, 15], [10, 7]], { to: 'main', x: 102, y: 17 });
    L.time = 320;
    return L;
  }

  // ───────────────────────── 1-3 Torre (subida vertical) ─────────────────────────
  function level3() {
    var H = 84;
    var L = new Level('1-3', 'Torre', 'tower', 34, H);
    L.vertical = true;
    L.fill(0, 1, 0, H - 1, 'S').fill(32, 33, 0, H - 1, 'S');
    L.ground(2, 31, H - 4);
    L.start = { x: 4, y: H - 6 };
    // Escalones en zigzag: cada uno sube 4 filas y queda a 2 columnas o menos del anterior, así cada salto se
    // alcanza caminando (el salto llega a ~5 filas). Los de piedra (S) no se atraviesan desde abajo: se suben por el
    // borde. Los de madera (=) se atraviesan desde abajo. [x, ancho, tipo, extra]
    var plan = [
      [17, 7, '='], [9, 7, '=', 'coins'], [16, 8, 'S', 'hog'], [7, 7, '='], [15, 7, '=', 'coins'], [23, 7, '=', 'bee'],
      [13, 8, 'S'], [4, 7, '=', 'coins'], [12, 7, '='], [21, 6, '=', 'bee'], [12, 8, 'S', 'hog'], [4, 6, '=', 'coins'],
      [11, 6, '='], [19, 8, '=', 'bee'], [11, 6, '=', 'coins'], [18, 10, 'S', 'hog'],
    ];
    var y = H - 8;
    L.steps = [];
    plan.forEach(function (p) {
      L.fill(p[0], p[0] + p[1] - 1, y, y, p[2]);
      L.steps.push({ x: p[0], w: p[1], y: y, solid: p[2] === 'S' });
      if (p[3] === 'coins') L.coins(p[0] + 2, y - 2, 3);
      if (p[3] === 'hog') L.enemy('hog', p[0] + 3, y - 1);
      if (p[3] === 'bee') L.enemy('bee', p[0] + 2, y - 5);
      y -= 4;
    });
    // Bloques con poder sobre el cuarto escalón (fila H-20): se golpean saltando desde él.
    L.row(8, H - 23, '?M?');
    // Meta: plataforma de un sentido de lado a lado (se sube desde abajo) con la bandera a la izquierda.
    L.fill(2, 31, y, y, '=');
    L.steps.push({ x: 2, w: 30, y: y, solid: false, goal: true });
    L.coins(14, y - 2, 6);
    L.flag(8, y);
    L.time = 300;
    return L;
  }

  // ───────────────────────── 1-4 Lago (agua y saltos largos) ─────────────────────────
  function level4() {
    var L = new Level('1-4', 'Lago', 'lake', 220, 26);
    L.start = { x: 3, y: 20 };
    L.ground(0, 30, 22);
    L.fill(31, 70, 21, 21, '~').fill(31, 70, 22, 24, 'w').fill(31, 70, 25, 25, 'S');
    L.row(36, 18, '===').row(44, 16, '===').row(52, 18, '===').row(60, 15, '====').coins(61, 13, 4);
    L.enemy('bee', 48, 12).enemy('bee', 64, 11);
    L.ground(71, 110, 22).row(76, 18, 'B?M?B').enemy('blob', 84, 21).enemy('hog', 92, 21).enemy('blob', 100, 21);
    L.pipe(104, 20, { to: 'r1', x: 4, y: 20 });
    // Tablones de 3 sobre una laguna (antes: tablones de 2 sobre un foso mortal).
    L.fill(111, 135, 21, 21, '~').fill(111, 135, 22, 24, 'w').fill(111, 135, 25, 25, 'S');
    L.row(112, 18, '===').row(117, 17, '===').row(122, 15, '===').row(127, 17, '===').row(132, 18, '===');
    L.coins(117, 15, 2).coins(122, 13, 2).coins(127, 15, 2);
    L.ground(136, 219, 22);
    L.fill(150, 165, 21, 21, '~').fill(150, 165, 22, 24, 'w').fill(150, 165, 25, 25, 'S');
    L.row(154, 17, '===').row(160, 18, '===');
    L.enemy('hog', 140, 21).enemy('blob', 145, 21).enemy('bee', 158, 12).enemy('blob', 172, 21).enemy('hog', 180, 21);
    L.row(170, 17, '?B?B?');
    L.stairs(188, 21, 8);
    L.flag(208, 22);
    [8, 74, 140, 176, 200].forEach(function (x) { L.bush(x, 22); });
    L.rooms.r1 = secretRoom('cave', [[6, 18], [7, 16], [12, 6]], { to: 'main', x: 108, y: 20 });
    L.time = 320;
    return L;
  }

  window.SRBLevels = [level1, level2, level3, level4];
})();
