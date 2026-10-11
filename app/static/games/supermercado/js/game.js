/*
 * Lógica de juego: rondas, lista, carrito, caja, pago, progreso, métricas y cámara.
 */
import * as THREE from 'three';
import { LEVELS, PRODUCTS, PRODUCT_BY_ID, SECTIONS, CHECKOUT, START, MAX_CART, REACH, MONEY, catName, productsOfCat, soles } from './config.js';
import { Spring, Tweens, clamp, lerp, rng, shuffle, store, easeOutCubic, easeInOutCubic, angleDiff } from './util.js';
import { Player } from './player.js';
import { Character, Shopper, LOOKS } from './actors.js';

const _v = new THREE.Vector3();
const _v2 = new THREE.Vector3();
const _m = new THREE.Matrix4();
const _m2 = new THREE.Matrix4();
const _q = new THREE.Quaternion();
const _q2 = new THREE.Quaternion();
const _e = new THREE.Euler();
const _s = new THREE.Vector3();
const _ray = new THREE.Raycaster();
const _ndc = new THREE.Vector2();
const _hit = new THREE.Vector3();

const SAVE_KEY = 'moscowle.supermercado.v1';
const OPT_KEY = 'moscowle.supermercado.opts';
const round2 = (x) => Math.round(x * 100) / 100;

/** Huecos dentro del canasto del carrito (coordenadas locales del carrito). */
const CART_SLOTS = (() => {
  const s = [];
  const layers = [0.34, 0.5, 0.65];
  const grid = [
    [-0.19, -0.1], [0.0, -0.1], [0.19, -0.1],
    [-0.19, 0.11], [0.0, 0.11], [0.19, 0.11],
  ];
  layers.forEach((y, l) => grid.forEach(([x, z], i) => s.push({ x: x + (l % 2 ? 0.06 : 0), y, z: z + (l % 2 ? -0.03 : 0), rot: ((i * 37) % 7) * 0.35 - 1 })));
  return s.slice(0, MAX_CART);
})();

export class Game {
  constructor(ctx) {
    Object.assign(this, ctx); // renderer, scene, camera, world, ui, audio, input, payment, fx
    this.tw = new Tweens();
    this.state = 'loading';
    this.time = 0;
    this.options = Object.assign(
      { sfx: true, music: true, reduced: matchMedia('(prefers-reduced-motion: reduce)').matches, calm: false },
      store.get(OPT_KEY, {}),
    );
    this.progress = Object.assign({ unlocked: 1, stars: {}, best: 0 }, store.get(SAVE_KEY, {}));
    if (new URLSearchParams(location.search).get('unlock') === '1') this.progress.unlocked = LEVELS.length;
    this.stats = {
      roundsStarted: 0,
      roundsFinished: 0,
      picks: 0,
      correctPicks: 0,
      wrongPicks: 0,
      paymentMistakes: 0,
      unitsRequired: 0,
      unitsCollectedClosed: 0,
      correctTimeSum: 0,
      correctTimeN: 0,
      levelReached: 0,
      score: 0,
    };
    this.round = null;
    this.keySeq = 1;
    this.cartItems = [];
    this.flying = [];
    this.target = null;
    this.hover = null;
    this.prevTarget = null;
    this.pointer = { x: 0, y: 0, moved: false, inside: false };
    this.shake = 0;
    this.hint = null;

    this.player = new Player(this.scene, this.world.vcMat);
    this.player.place(START.x, START.z, START.heading);
    this.player.onBump = (v) => this.onBump(v);

    // cajera
    this.cashier = new Character(LOOKS.cashier, this.world.vcMat);
    this.cashier.pushing = false;
    this.cashier.root.position.set(CHECKOUT.counterX + 0.78, 0, this.world.scanZ + 0.15);
    this.cashier.root.rotation.y = -Math.PI / 2;
    this.cashier.setArms(0.05, 0.05);
    this.scene.add(this.cashier.root);

    // clientes (distracción)
    this.shoppers = [
      new Shopper(this.scene, this.world.vcMat, LOOKS.shopperA, [[-11.4, 1.35], [-0.6, 1.35], [-0.6, -2.9], [-11.4, -2.9]], 0x95e7ff, 0xfff3dc, 1.15),
      new Shopper(this.scene, this.world.vcMat, LOOKS.shopperB, [[0.0, -7.4], [0.0, -2.9], [7.0, -2.9], [7.0, -7.4]], 0x8fc4b8, 0xffd28f, 1.35),
    ];
    this.shoppers.forEach((s, i) => {
      s.reset(i);
      s.group.visible = false;
      s.active = false;
    });
    this.carts = [this.player.cart, ...this.shoppers.map((s) => s.cart)];

    // flecha de pista sobre el jugador
    this.hintArrow = new THREE.Mesh(
      new THREE.ConeGeometry(0.16, 0.42, 4).rotateX(Math.PI / 2),
      new THREE.MeshStandardMaterial({ color: 0xffd23f, emissive: 0xb07a00, emissiveIntensity: 0.6, roughness: 0.4 }),
    );
    this.hintArrow.visible = false;
    this.scene.add(this.hintArrow);

    // cámara con resortes
    this.cam = {
      mode: 'title',
      px: new Spring(0, 3, 1), py: new Spring(12, 3, 1), pz: new Spring(16, 3, 1),
      lx: new Spring(0, 3, 1), ly: new Spring(0, 3, 1), lz: new Spring(0, 3, 1),
      orbit: 0,
    };
    this.applyOptions();
    this.bindUI();
    this.bindPointer();
    this.exposeDebug();
  }

  /* ================================================================ opciones y progreso */

  applyOptions() {
    const o = this.options;
    this.audio.setSfx(o.sfx);
    this.audio.setMusic(o.music);
    this.player.calm = o.calm;
    this.player.char.reduced = o.reduced;
    document.body.classList.toggle('reduced', o.reduced);
    document.getElementById('optSfx').checked = o.sfx;
    document.getElementById('optMusic').checked = o.music;
    document.getElementById('optReduced').checked = o.reduced;
    document.getElementById('optCalm').checked = o.calm;
    store.set(OPT_KEY, o);
  }

  saveProgress() {
    store.set(SAVE_KEY, this.progress);
  }

  /* ================================================================ interfaz */

  bindUI() {
    const $ = (id) => document.getElementById(id);
    const ui = this.ui;
    const click = (id, fn) =>
      $(id).addEventListener('click', () => {
        this.audio.unlock();
        this.audio.click();
        fn();
      });
    click('btnPlay', () => this.openBrief(Math.min(this.progress.unlocked, LEVELS.length)));
    click('btnLevels', () => {
      ui.renderLevels(this.progress, (n) => this.openBrief(n));
      ui.show('scrLevels');
    });
    click('btnOptions', () => ui.show('scrOptions'));
    click('btnExit', () => this.exitGame());
    click('btnGo', () => this.beginPlay());
    click('btnResume', () => this.resume());
    click('btnRestart', () => {
      const n = this.round.level.n;
      this.closeRound();
      this.openBrief(n, { fresh: true });
    });
    click('btnPauseOpts', () => ui.show('scrOptions'));
    click('btnToMenu', () => this.toMenu());
    click('btnWinMenu', () => this.toMenu());
    click('btnWinAgain', () => this.openBrief(this.round.level.n));
    click('btnWinNext', () => this.openBrief(Math.min(this.round.level.n + 1, LEVELS.length)));
    click('pauseBtn', () => this.pause());
    click('hintBtn', () => this.showHint());
    click('peekBtn', () => this.peek());
    for (const [id, key] of [['optSfx', 'sfx'], ['optMusic', 'music'], ['optReduced', 'reduced'], ['optCalm', 'calm']]) {
      $(id).addEventListener('change', (e) => {
        this.audio.unlock();
        this.options[key] = e.target.checked;
        this.applyOptions();
        this.audio.click();
      });
    }
    ui.onReturn = (key) => this.returnItem(key);
    ui.onBack = (cur, prev) => {
      // volver desde opciones de pausa → pausa; desde el briefing → menú
      if (cur === 'scrBrief') {
        this.toMenu();
        return true;
      }
      if (cur === 'scrBye') {
        ui.show('scrTitle', { push: false });
        return true;
      }
      return false;
    };
    this.input.onTouchMode = (on) => ui.setTouch(on);
    ui.setTouch(this.input.touchMode);
    // el primer gesto habilita el audio
    addEventListener('pointerdown', () => this.audio.unlock(), { once: true });
    addEventListener('keydown', () => this.audio.unlock(), { once: true });
  }

  bindPointer() {
    const el = this.renderer.domElement;
    el.addEventListener('pointermove', (e) => {
      this.pointer.x = e.clientX;
      this.pointer.y = e.clientY;
      this.pointer.moved = true;
      this.pointer.inside = true;
    });
    el.addEventListener('pointerleave', () => {
      this.pointer.inside = false;
      this.hover = null;
    });
    el.addEventListener('pointerdown', (e) => {
      if (this.state === 'checkout') this.hurry();
      if (this.state !== 'play') return;
      this.pointer.x = e.clientX;
      this.pointer.y = e.clientY;
      this.pointer.inside = true;
      const col = this.pickColumnAt(e.clientX, e.clientY);
      if (col) {
        this.hover = col;
        if (this.inReach(col, 2.4)) this.pick(col);
        else {
          this.ui.toast('¡Acércate un poco más!', 'soft', 'Camina hasta el estante para tomarlo', 1600);
          this.audio.soft();
        }
      } else if (e.pointerType !== 'mouse') {
        // tocar el piso en la caja también sirve para pagar
        if (this.atCheckout()) this.tryCheckout();
      }
    });
  }

  /* ================================================================ flujo de pantallas */

  showTitle() {
    this.state = 'title';
    this.cam.mode = 'title';
    this.ui.hud(false);
    this.ui.show('scrTitle', { push: false });
    this.ui.stack.length = 0;
  }

  toMenu() {
    if (this.round && !this.round.closed) this.closeRound();
    this.clearCart(true);
    this.world.restock();
    this.shoppers.forEach((s) => (s.group.visible = s.active = false));
    this.player.place(START.x, START.z, START.heading);
    this.world.beacon.visible = false;
    this.ui.goPay(false);
    this.ui.hideBubble();
    this.ui.npcSay(null);
    this.showTitle();
  }

  /** Genera la ronda y muestra el resumen del nivel. */
  openBrief(n, { seed, fresh } = {}) {
    if (this.round && !this.round.closed) this.closeRound();
    const L = LEVELS[n - 1];
    this.clearCart(true);
    this.world.restock();
    this.round = this.makeRound(L, seed ?? (Date.now() & 0xffffff));
    this.ui.renderBrief(L, this.round);
    this.ui.hud(false);
    this.state = 'brief';
    this.cam.mode = 'title';
    this.player.place(START.x, START.z, START.heading);
    this.ui.goPay(false);
    this.world.beacon.visible = false;
    this.ui.show('scrBrief', { push: false });
    this.ui.stack = ['scrTitle'];
  }

  makeRound(L, seed) {
    const rand = rng(seed);
    let cats = [];
    const pool = PRODUCTS.filter((p) => L.sections.includes(p.sec));
    const allCats = [...new Set(pool.map((p) => p.cat))];
    const variantCats = allCats.filter((c) => productsOfCat(c).length > 1);
    let candidates = allCats.filter((c) => {
      const ps = productsOfCat(c);
      if (L.intOnly) return ps.length === 1 && ps[0].price % 100 === 0;
      return true;
    });
    shuffle(candidates, rand);
    if (L.budget) {
      const v = shuffle(variantCats.slice(), rand).slice(0, Math.min(3, variantCats.length));
      cats = v.concat(candidates.filter((c) => !v.includes(c))).slice(0, L.items);
    } else cats = candidates.slice(0, L.items);
    const list = cats.map((cat) => {
      const ps = productsOfCat(cat);
      let qty = 1;
      if (L.maxQty > 1 && ps[0].countable && rand() < 0.6) qty = 2 + Math.floor(rand() * (L.maxQty - 1));
      return { cat, qty, got: 0 };
    });
    // presupuesto: alcanza eligiendo bien, no si se elige lo más caro
    let budget = 0;
    if (L.budget) {
      let cheap = 0;
      let exp = 0;
      for (const e of list) {
        const prices = productsOfCat(e.cat).map((p) => p.price);
        cheap += Math.min(...prices) * e.qty;
        exp += Math.max(...prices) * e.qty;
      }
      budget = Math.ceil((cheap + (exp - cheap) * 0.4) / 100) * 100;
      if (budget >= exp) budget = Math.max(cheap, exp - 50);
    }
    return {
      level: L,
      seed,
      list,
      budget,
      calm: this.options.calm,
      elapsed: 0,
      memLeft: L.memory,
      peekLeft: 0,
      peeks: 0,
      wrong: 0,
      payMistakes: 0,
      lastCorrectAt: 0,
      score: 0,
      started: false,
      closed: false,
      finished: false,
    };
  }

  beginPlay() {
    const r = this.round;
    if (!r) return;
    r.started = true;
    this.stats.roundsStarted++;
    this.stats.unitsRequired += r.list.reduce((a, e) => a + e.qty, 0);
    this.ui.hideAll();
    this.ui.hud(true);
    ['listCard', 'topRight', 'cartBar'].forEach((id) => (document.getElementById(id).style.visibility = ''));
    this.ui.setList(r.list, r.level.memory > 0);
    this.ui.setCart([], !!r.budget, 0);
    this.ui.setBudget(r.budget, 0);
    this.ui.setTimer(!r.calm, r.level.time, 1);
    this.ui.goPay(false);
    requestAnimationFrame(() => this.ui.layoutTop());
    this.state = 'play';
    this.cam.mode = 'play';
    this.cam.px.omega = this.cam.py.omega = this.cam.pz.omega = 2.4;
    this.cam.lx.omega = this.cam.ly.omega = this.cam.lz.omega = 2.4;
    this.tw.add(1.6, () => {}, { done: () => this.setCamOmega(5) });
    // clientes
    this.shoppers.forEach((s, i) => {
      const on = i < r.level.npcs;
      s.active = on;
      s.group.visible = on;
      if (on) s.reset(i === 0 ? 1 : 2);
    });
    this.input.clearPulses();
    this.ui.toast(r.level.memory ? '¡Memoriza tu lista!' : '¡A comprar!', 'good', r.level.memory ? `Se esconde en ${r.level.memory} segundos` : 'Busca lo que dice tu lista', 2000);
    this.audio.good();
  }

  setCamOmega(w) {
    const c = this.cam;
    c.px.omega = c.py.omega = c.pz.omega = w;
    c.lx.omega = c.ly.omega = c.lz.omega = w * 1.1;
  }

  pause() {
    if (this.state !== 'play') return;
    this.state = 'paused';
    this.ui.show('scrPause', { push: false });
    this.ui.stack = [];
    this.audio.setRattle(0);
  }

  resume() {
    if (this.state !== 'paused') return;
    this.ui.hideAll();
    this.state = 'play';
    this.input.clearPulses();
  }

  /** Cierra una ronda (terminada o abandonada) y acumula lo recogido. */
  closeRound() {
    const r = this.round;
    if (!r || r.closed) return;
    r.closed = true;
    if (r.started) this.stats.unitsCollectedClosed += this.roundCollected(r);
  }

  roundCollected(r) {
    return r.list.reduce((a, e) => a + Math.min(e.got, e.qty), 0);
  }

  exitGame() {
    const res = this.stats.roundsStarted ? this.result() : null;
    const done = () => {
      if (window.MoscowleGame && window.MoscowleGame.embedded) window.MoscowleGame.exit();
      else this.ui.show('scrBye');
    };
    if (res && window.MoscowleGame) window.MoscowleGame.finish(res).then(done, done);
    else done();
  }

  /* ================================================================ resultado (métricas de la sesión) */

  result() {
    const s = this.stats;
    const started = s.roundsStarted;
    const live = this.round && this.round.started && !this.round.closed ? this.roundCollected(this.round) : 0;
    return {
      game_name: 'Supermercado',
      accuracy: s.picks ? round2((s.correctPicks / s.picks) * 100) : 0,
      avg_time: s.correctTimeN ? round2(s.correctTimeSum / s.correctTimeN) : 0,
      level_reached: s.levelReached,
      deaths: null,
      coins: null,
      score: s.score,
      kpis: {
        completion: started ? round2((s.roundsFinished / started) * 100) : 0,
        errors: started ? round2((s.wrongPicks + s.paymentMistakes) / started) : 0,
        collected: s.unitsRequired ? round2(((s.unitsCollectedClosed + live) / s.unitsRequired) * 100) : 0,
      },
    };
  }

  /* ================================================================ estantes y carrito */

  columnDist(col, x, z) {
    const cx = clamp(x, col.x - 0.5, col.x + 0.5);
    return Math.hypot(x - cx, z - col.front);
  }

  inReach(col, reach = REACH) {
    const p = this.player;
    // el jugador debe estar delante del mueble
    if (p.pos.y < col.front - 0.2 && p.cartWorld.y < col.front - 0.2) return false;
    return Math.min(this.columnDist(col, p.cartWorld.x, p.cartWorld.y), this.columnDist(col, p.pos.x, p.pos.y) - 0.3) < reach;
  }

  nearestColumn() {
    const p = this.player;
    let best = null;
    let bd = REACH;
    for (const col of this.world.columns) {
      if (Math.abs(col.x - p.cartWorld.x) > 3 || Math.abs(col.front - p.cartWorld.y) > 3) continue;
      if (p.cartWorld.y < col.front - 0.2) continue;
      let d = this.columnDist(col, p.cartWorld.x, p.cartWorld.y);
      // prioriza lo que el carrito "mira"
      const dx = col.x - p.cartWorld.x;
      const dz = col.front - p.cartWorld.y;
      const dl = Math.hypot(dx, dz) || 1;
      const facing = (dx * p.fx + dz * p.fz) / dl;
      d -= facing * 0.25;
      if (!this.world.nextSlot(col)) d += 0.5;
      if (d < bd) {
        bd = d;
        best = col;
      }
    }
    return best;
  }

  pickColumnAt(x, y) {
    const r = this.renderer.domElement.getBoundingClientRect();
    _ndc.set(((x - r.left) / r.width) * 2 - 1, -((y - r.top) / r.height) * 2 + 1);
    _ray.setFromCamera(_ndc, this.camera);
    let best = null;
    let bd = Infinity;
    for (const col of this.world.columns) {
      if (_ray.ray.intersectBox(col.box, _hit)) {
        const d = _hit.distanceToSquared(_ray.ray.origin);
        if (d < bd) {
          bd = d;
          best = col;
        }
      }
    }
    return best;
  }

  entryFor(p) {
    const list = this.round.list;
    for (let i = 0; i < list.length; i++) if (list[i].cat === p.cat) return i;
    return -1;
  }

  pick(col) {
    if (this.state !== 'play') return false;
    const r = this.round;
    const p = col.product;
    if (this.cartItems.length >= MAX_CART) {
      this.ui.toast('¡Tu carrito está lleno!', 'soft', 'Devuelve algo o ve a la caja');
      this.audio.soft();
      return false;
    }
    const slot = this.world.nextSlot(col);
    if (!slot) {
      this.ui.toast('Ya no quedan aquí', 'soft');
      return false;
    }
    const ei = this.entryFor(p);
    const correct = ei >= 0 && r.list[ei].got < r.list[ei].qty;
    this.stats.picks++;
    if (correct) {
      this.stats.correctPicks++;
      r.list[ei].got++;
      const gap = r.elapsed - r.lastCorrectAt;
      r.lastCorrectAt = r.elapsed;
      this.stats.correctTimeSum += gap;
      this.stats.correctTimeN++;
      r.score += 100;
    } else {
      this.stats.wrongPicks++;
      r.wrong++;
    }
    // la unidad sale del estante y vuela al carrito
    slot.taken = true;
    const used = new Set(this.cartItems.map((it) => it.cartSlot));
    let cs = 0;
    while (used.has(cs)) cs++;
    const it = {
      key: this.keySeq++,
      product: p,
      wrong: !correct,
      entry: correct ? ei : -1,
      cartSlot: cs,
      col,
      slot,
      state: 'fly',
      t: 0,
      dur: 0.55,
      from: slot.pos.clone(),
      fromRot: slot.rotY,
      squash: new Spring(1, 18, 0.32),
    };
    this.cartItems.push(it);
    this.flying.push(it);
    this.audio.pick();
    this.player.char.bounce(0.12);
    if (correct) {
      this.ui.updateList(r.list, ei);
      if (this.listComplete()) this.onListComplete();
    } else {
      const e = ei >= 0 ? r.list[ei] : null;
      if (e) this.ui.toast(`Ya tienes ${e.qty === 1 ? 'tu' : 'tus'} ${catName(e.cat, e.qty).toLowerCase()}`, 'soft', 'Toca la ficha roja del carrito para devolverlo', 2600);
      else this.ui.toast(`Mmm… ${p.name.toLowerCase()} no está en tu lista`, 'soft', 'Puedes devolverlo: toca la ficha roja del carrito', 2600);
      this.audio.soft();
    }
    this.refreshCartUI();
    return true;
  }

  listComplete() {
    return this.round.list.every((e) => e.got >= e.qty);
  }

  onListComplete() {
    this.ui.goPay(true);
    this.world.beacon.visible = true;
    this.tw.add(0.4, () => {}, { delay: 0.5, done: () => this.audio.good() });
  }

  cartTotal(onlyCorrect = false) {
    let t = 0;
    for (const it of this.cartItems) if (!onlyCorrect || !it.wrong) t += it.product.price;
    return t;
  }

  refreshCartUI() {
    const r = this.round;
    this.ui.setCart(this.cartItems, !!r.budget, this.cartTotal());
    this.ui.setBudget(r.budget, this.cartTotal());
  }

  returnItem(key) {
    if (this.state !== 'play') return;
    const idx = this.cartItems.findIndex((it) => it.key === key);
    if (idx < 0) return;
    const it = this.cartItems[idx];
    if (it.state !== 'in') return;
    this.cartItems.splice(idx, 1);
    const r = this.round;
    if (!it.wrong && it.entry >= 0) {
      const e = r.list[it.entry];
      const wasComplete = this.listComplete();
      e.got = Math.max(0, e.got - 1);
      this.ui.updateList(r.list, -1);
      if (wasComplete) {
        this.ui.goPay(false);
        this.world.beacon.visible = false;
      }
    } else if (it.wrong) {
      // devolver lo que no iba en la lista es un acierto de autocorrección: un pequeño premio
      r.score += 10;
    }
    // vuela de regreso a su lugar en el estante
    this.itemWorldMatrix(it, _m);
    _m.decompose(_v, _q, _s);
    it.state = 'back';
    it.t = 0;
    it.from = _v.clone();
    const dist = it.from.distanceTo(it.slot.pos);
    it.dur = clamp(0.35 + dist * 0.08, 0.45, 1.0);
    this.flying.push(it);
    this.audio.whoosh();
    this.ui.toast(it.wrong ? '¡Bien! Lo devolviste' : 'Devuelto al estante', it.wrong ? 'good' : '', '', 1300);
    this.refreshCartUI();
  }

  returnLast() {
    for (let i = this.cartItems.length - 1; i >= 0; i--) if (this.cartItems[i].wrong && this.cartItems[i].state === 'in') return this.returnItem(this.cartItems[i].key);
    const last = this.cartItems[this.cartItems.length - 1];
    if (last && last.state === 'in') this.returnItem(last.key);
  }

  clearCart(silent) {
    this.cartItems.length = 0;
    this.flying.length = 0;
    this.checkoutItems = null;
    if (!silent) this.ui.setCart([], false, 0);
    else {
      document.getElementById('cartChips').innerHTML = '';
      document.getElementById('cartCount').textContent = '0';
    }
  }

  /** Matriz mundial de un producto dentro del carrito (con su acomodo, rebote y meneo). */
  itemWorldMatrix(it, out) {
    const s = CART_SLOTS[it.cartSlot];
    const cart = this.player.cart;
    const sq = it.squash.x;
    const jig = this.cartJiggle;
    const layer = it.cartSlot / 6 | 0;
    _e.set(jig.z * (0.6 + layer * 0.4), s.rot, -jig.x * (0.6 + layer * 0.4));
    _q.setFromEuler(_e);
    const k = 0.74;
    _s.set(k * (1 + (1 - sq) * 0.6), k * sq, k * (1 + (1 - sq) * 0.6));
    _m2.compose(_v2.set(s.x + jig.x * 0.04 * (layer + 1), s.y - 0.06, s.z + jig.z * 0.04 * (layer + 1)), _q, _s);
    return out.multiplyMatrices(cart.mesh.matrixWorld, _m2);
  }

  /* ================================================================ caja */

  atCheckout() {
    const p = this.player;
    return Math.hypot(p.pos.x - CHECKOUT.padX, p.pos.y - CHECKOUT.padZ) < CHECKOUT.padR + 0.2;
  }

  async tryCheckout(force = false) {
    if (this.state !== 'play') return;
    if (this.flying.length) return;
    const r = this.round;
    if (!this.cartItems.length) {
      this.ui.toast('Tu carrito está vacío', 'soft', 'Primero busca lo de tu lista');
      this.audio.soft();
      return;
    }
    if (!this.cartItems.some((it) => !it.wrong)) {
      this.ui.toast('Nada de tu carrito está en la lista', 'soft', 'Busca primero lo que dice tu lista');
      this.audio.soft();
      return;
    }
    if (!force) {
      const missing = r.list.filter((e) => e.got < e.qty);
      if (missing.length) {
        this.state = 'dialog';
        const n = missing.reduce((a, e) => a + e.qty - e.got, 0);
        const text = r.level.memory
          ? `Todavía te ${n === 1 ? 'falta 1 cosa' : `faltan ${n} cosas`} de tu lista.`
          : `Te falta: <b>${missing.map((e) => `${e.qty - e.got} ${catName(e.cat, e.qty - e.got).toLowerCase()}`).join(', ')}</b>.`;
        const v = await this.ui.dialog('¿Ya terminaste?', text, [
          { label: 'Pagar así', value: 'pay', cls: 'ghost' },
          { label: 'Seguir comprando', value: 'shop', cls: 'big' },
        ]);
        this.state = 'play';
        this.input.clearPulses();
        if (v !== 'pay') return;
      }
      const total = this.cartTotal(true);
      if (r.budget && total > r.budget) {
        this.state = 'dialog';
        this.stats.paymentMistakes++;
        r.payMistakes++;
        await this.ui.dialog(
          '¡Uy! No te alcanza',
          `Tu compra suma <b>${soles(total)}</b> y tienes <b>${soles(r.budget)}</b>.<br>Devuelve algo caro y elige uno más barato.`,
          [{ label: 'Entendido', value: 1, cls: 'big' }],
        );
        this.state = 'play';
        this.input.clearPulses();
        return;
      }
    }
    this.startCheckout();
  }

  async startCheckout() {
    const r = this.round;
    this.state = 'checkout';
    this.ui.hideBubble();
    this.ui.goPay(false);
    this.world.beacon.visible = false;
    this.world.outline.visible = false;
    this.resetWiggle();
    this.target = null;
    this.ui.hud(false);
    document.getElementById('hud').classList.remove('hidden');
    ['listCard', 'topRight', 'cartBar'].forEach((id) => (document.getElementById(id).style.visibility = 'hidden'));
    this.player.auto = { x: CHECKOUT.padX, z: CHECKOUT.z0, heading: 0 };
    this.cam.mode = 'checkout';
    this.setCamOmega(2.2);
    this.audio.setRattle(0);
    const reg = this.world.register;
    reg.show('¡Hola!', 'Bienvenido');
    this.cashier.lookYaw = -0.5;
    this.cashier.setArms(-2.6, 0.05, 0.4, -0.1); // saluda
    this.tw.scale = 1;
    this.ui.toast('¡Hola! Pon tus cosas en la cinta', '', this.input.touchMode ? 'Toca la pantalla para ir más rápido' : 'Presiona E para ir más rápido', 2400);
    await this.tw.wait(1.2);
    this.cashier.setArms(0.05, 0.05);
    const tw = this.tw;
    const W = this.world;
    let total = 0;
    const items = this.cartItems.slice();
    this.checkoutItems = items;
    W.bag.visible = true;
    W.bag.scale.setScalar(0.001);
    tw.to(0.5, (k) => W.bag.scale.setScalar(Math.max(0.001, k)), { ease: (t) => 1 + 2.7 * Math.pow(t - 1, 3) + 1.7 * Math.pow(t - 1, 2) });
    const aside = [];
    for (let i = 0; i < items.length; i++) {
      const it = items[i];
      it.state = 'checkout';
      this.itemWorldMatrix(it, _m);
      _m.decompose(_v, _q, _s);
      const from = _v.clone();
      const fromQ = _q.clone();
      const beltA = W.beltStart.clone();
      const beltB = W.beltEnd.clone();
      const scan = W.scanPos.clone();
      const size = 0.78;
      // 1) del carrito a la cinta
      await tw.to(0.26, (k) => {
        _v.lerpVectors(from, beltA, k);
        _v.y += Math.sin(k * Math.PI) * 0.5;
        _q.copy(fromQ).slerp(IDQ, k);
        _s.setScalar(lerp(0.74, size, k));
        _m.compose(_v, _q, _s);
        W.setSlot(it.slot, _m);
      }, { ease: easeInOutCubic });
      this.audio.land(i % 3);
      // 2) la cinta lo lleva al escáner
      W.beltTex.userData.moving = true;
      this.cashier.setArms(0.05, -0.9, 0.1, 0.25);
      await tw.to(0.36, (k) => {
        _v.lerpVectors(beltA, beltB, k);
        _m.compose(_v, IDQ, _s.setScalar(size));
        W.setSlot(it.slot, _m);
      }, { ease: easeOutCubic });
      W.beltTex.userData.moving = false;
      // 3) la cajera lo pasa por el escáner
      this.cashier.setArms(0.05, -1.45, 0.1, 0.5);
      await tw.to(0.22, (k) => {
        _v.lerpVectors(beltB, scan, k);
        _v.y += Math.sin(k * Math.PI) * 0.15;
        _e.set(0, k * 0.8, 0);
        _q.setFromEuler(_e);
        _m.compose(_v, _q, _s.setScalar(size));
        W.setSlot(it.slot, _m);
      });
      W.laser.material.opacity = 1;
      this.tw.add(0.25, (k) => (W.laser.material.opacity = 1 - k));
      if (it.wrong) {
        this.audio.soft();
        reg.show('—', 'No estaba en tu lista');
        aside.push(it);
        const asideTo = new THREE.Vector3(CHECKOUT.counterX - 0.05, 0.84, W.scanPos.z - 0.9 + aside.length * 0.02);
        asideTo.x += 0.18 * ((aside.length - 1) % 2 ? 1 : -1);
        await tw.to(0.35, (k) => {
          _v.lerpVectors(scan, asideTo, k);
          _v.y += Math.sin(k * Math.PI) * 0.3;
          _m.compose(_v, IDQ, _s.setScalar(size));
          W.setSlot(it.slot, _m);
        });
      } else {
        total += it.product.price;
        this.audio.beep();
        reg.show(soles(total), it.product.name);
        this.fx.sparkle(scan.x, scan.y + 0.2, scan.z, 0x9ff0b8, 6);
        // 4) a la bolsa
        const bag = W.bagPos.clone();
        bag.y += 0.25;
        tw.to(0.4, (k) => {
          _v.lerpVectors(scan, bag, k);
          _v.y += Math.sin(k * Math.PI) * 0.35;
          _m.compose(_v, IDQ, _s.setScalar(size * (1 - k * 0.6)));
          W.setSlot(it.slot, _m);
          if (k >= 1) {
            W.hideSlot(it.slot);
            W.bag.scale.setScalar(1.12);
            tw.to(0.25, (q) => W.bag.scale.setScalar(1.12 - 0.12 * q));
          }
        });
      }
      this.cashier.setArms(0.05, 0.05);
      await tw.wait(0.05);
    }
    tw.scale = 1;
    this.cashier.setArms(0.05, 0.05);
    await tw.wait(0.4);
    reg.show(soles(total), 'Total a pagar');
    this.audio.register();
    this.cashier.lookYaw = -0.4;
    await tw.wait(0.7);
    // pago
    r.total = total;
    this.state = 'pay';
    const wallet = this.makeWallet(total, r);
    this.ui.show('scrPay', { push: false });
    const res = await this.payment.open({
      items: items.map((it) => ({ name: it.product.name, price: it.product.price, icon: this.ui.icons[it.product.id], aside: it.wrong })),
      total,
      wallet,
      mode: r.level.pay,
    });
    this.payment.close && this.payment.close();
    this.ui.show(null, { push: false });
    this.stats.paymentMistakes += res.mistakes;
    r.payMistakes += res.mistakes;
    r.paid = res.paid;
    r.change = res.change;
    reg.show(res.change > 0 ? soles(res.change) : '¡Gracias!', res.change > 0 ? 'Tu vuelto' : 'Vuelve pronto');
    this.finishRound(aside);
  }

  /** Billetera según el tipo de pago del nivel (céntimos). */
  makeWallet(total, r) {
    const mode = r.level.pay;
    const denoms = MONEY.map((m) => m.v).sort((a, b) => b - a);
    const exact = [];
    let rest = total;
    for (const d of denoms) {
      while (rest >= d) {
        exact.push(d);
        rest -= d;
      }
    }
    const rand = rng(r.seed + 99);
    if (r.budget) {
      const w = [];
      let b = r.budget;
      for (const d of [2000, 1000, 500, 200, 100]) while (b >= d) { w.push(d); b -= d; }
      if (b > 0) w.push(b >= 50 ? 50 : 10);
      return w;
    }
    if (mode === 'exact') {
      const extra = [100, 50, 20, 200, 10];
      return exact.concat([extra[Math.floor(rand() * 3)], extra[3 + Math.floor(rand() * 2)]]);
    }
    if (mode === 'auto') {
      const big = [500, 1000, 2000].find((d) => d > total) || 2000;
      return exact.concat(total > 2000 ? [2000, 1000] : [big]);
    }
    // 'change': solo billetes grandes + unas monedas que no alcanzan para pagar justo
    let w = [];
    if (total <= 500) w = [500];
    else if (total <= 1000) w = [1000];
    else if (total <= 2000) w = [2000];
    else if (total <= 3000) w = [2000, 1000];
    else w = [2000, 2000];
    if (w.reduce((a, b) => a + b, 0) === total) w.push(1000);
    const small = [20, 50, 10];
    let s = 0;
    for (const c of small) if (s + c < total && rand() < 0.7) { w.push(c); s += c; }
    return w;
  }

  finishRound(aside) {
    const r = this.round;
    const L = r.level;
    const complete = this.listComplete();
    this.closeRound();
    r.finished = true;
    this.stats.roundsFinished++;
    const s1 = complete;
    const s2 = r.wrong === 0 && r.payMistakes === 0;
    const s3 = r.calm ? r.peeks === 0 : r.elapsed <= L.time;
    let stars = (s1 ? 1 : 0) + (s2 ? 1 : 0) + (s3 ? 1 : 0);
    if (!s1) stars = Math.min(stars, 1);
    stars = Math.max(1, stars);
    if (complete) this.stats.levelReached = Math.max(this.stats.levelReached, L.n);
    const timeBonus = r.calm ? 0 : Math.max(0, Math.round((L.time - r.elapsed) * 2));
    r.score += (r.payMistakes === 0 ? 50 : 0) + timeBonus + stars * 100 - r.peeks * 25;
    r.score = Math.max(0, r.score);
    this.stats.score += r.score;
    // progreso guardado
    if (complete) {
      this.progress.stars[L.n] = Math.max(this.progress.stars[L.n] || 0, stars);
      this.progress.unlocked = Math.max(this.progress.unlocked, Math.min(LEVELS.length, L.n + 1));
    }
    this.progress.best = Math.max(this.progress.best || 0, r.score);
    this.saveProgress();
    // celebración
    this.state = 'win';
    this.cam.mode = 'win';
    this.setCamOmega(1.8);
    const W = this.world;
    this.fx.confetti(this.player.pos.x + 0.5, 2.2, this.player.pos.y + 0.6, this.options.reduced ? 50 : 150);
    this.audio.win();
    this.player.char.pushing = false;
    this.player.char.setArms(-2.8, -2.8, 0.3, -0.3);
    this.player.char.bounce(0.4);
    this.cashier.setArms(-2.7, 0.05, 0.4, -0.1);
    const units = this.roundCollected(r);
    const need = r.list.reduce((a, e) => a + e.qty, 0);
    const lines = [
      { k: 'Lista', v: `${units} de ${need}` },
      { k: 'Pagaste', v: soles(r.paid || 0) },
    ];
    if ((r.change || 0) > 0) lines.push({ k: 'Vuelto', v: soles(r.change) });
    if (r.budget) lines.push({ k: 'Te sobró', v: soles(Math.max(0, r.budget - (r.total || 0))) });
    lines.push({ k: 'Puntos', v: `+${r.score}`, big: true });
    const titles = complete ? ['¡Compra lista!', '¡Excelente compra!', '¡Súper compra!'] : ['¡Buen intento!'];
    this.ui.renderWin({ title: titles[Math.min(titles.length - 1, stars - 1)], stars, lines, hasNext: complete && L.n < LEVELS.length });
    this.tw.add(1.3, () => {}, {
      done: () => {
        this.ui.show('scrWin', { push: false });
        this.ui.stack = [];
      },
    });
    // lo comprado ya está en la bolsa; lo apartado queda en el mostrador hasta reponer
    for (const it of this.cartItems) if (!it.wrong) W.hideSlot(it.slot);
    this.cartItems.length = 0;
  }

  /* ================================================================ ayudas */

  /** En la caja, tocar o presionar acción acelera la cinta. */
  hurry() {
    if (this.tw.scale > 1) return;
    this.tw.scale = 2.6;
    this.ui.toast('¡Más rápido!', 'good', '', 900);
  }

  peek() {
    const r = this.round;
    if (this.state !== 'play' || !r || !r.level.memory || r.memLeft > 0 || r.peekLeft > 0) return;
    r.peeks++;
    r.peekLeft = 3;
    this.ui.cover(false);
    this.audio.click();
  }

  showHint() {
    if (this.state !== 'play') return;
    const r = this.round;
    const p = this.player;
    let best = null;
    let bd = Infinity;
    if (this.listComplete()) {
      this.hint = { x: CHECKOUT.padX, z: CHECKOUT.padZ, t: 4, col: null };
      this.ui.toast('¡Ve a la caja!', 'good', 'Sigue la flecha');
      return;
    }
    for (const col of this.world.columns) {
      const ei = this.entryFor(col.product);
      if (ei < 0 || r.list[ei].got >= r.list[ei].qty) continue;
      const d = Math.hypot(col.x - p.pos.x, col.front - p.pos.y);
      if (d < bd) {
        bd = d;
        best = col;
      }
    }
    if (!best) return;
    this.hint = { x: best.x, z: best.front + 0.7, t: 5, col: best };
    this.ui.toast('¡Por aquí!', 'good', 'Sigue la flecha amarilla', 1600);
    this.audio.good();
  }

  onBump(v) {
    this.audio.bump();
    if (!this.options.reduced) this.shake = Math.min(0.25, v * 0.05);
    this.player.cart.bump.v += v * 0.6;
    this.player.char.bounce(0.15);
    for (const it of this.cartItems) if (it.state === 'in') it.squash.v -= v * 0.8;
  }

  resetWiggle() {
    if (this.prevTarget) {
      for (const s of this.prevTarget.slots) if (!s.taken) this.world.setSlot(s, this.world.slotMatrix(s, 0, 0, 1, _m));
      this.prevTarget = null;
    }
  }

  /* ================================================================ actualización por frame */

  update(dt) {
    this.time += dt;
    this.tw.update(dt);
    const st = this.state;
    const input = this.input;
    const move = input.poll();
    if (st === 'play') this.updatePlay(dt, move);
    else {
      if (input.take('action') && st === 'checkout') this.hurry();
      if (input.take('pause') && st === 'paused') this.resume();
      input.take('back');
      input.take('peek');
    }
    if (st === 'checkout' || st === 'pay' || st === 'win') {
      this.player.update(dt, { x: 0, y: 0 }, false, this.world.colliders, null);
    }
    if (st === 'title' || st === 'brief') {
      // el niño espera en la entrada con un pequeño vaivén
      this.player.char.update(dt, 0, 0, 0);
    }
    if (st !== 'checkout' && st !== 'pay' && st !== 'win') {
      this.player.auto = null;
      if (st !== 'win') this.player.char.pushing = true;
    }
    // clientes
    for (const s of this.shoppers) if (s.active && (st === 'play' || st === 'checkout' || st === 'pay')) s.update(dt, this.player);
    this.cartJiggleUpdate(dt);
    this.updateFlying(dt);
    this.updateCartItems(dt);
    this.cashierUpdate(dt);
    this.world.updateArch(this.player.pos.x, this.player.pos.y, dt);
    if (this.world.beltTex.userData.moving) this.world.beltTex.offset.y -= dt * 1.4;
    // ruedas y sombras redondas
    this.wheels.update(this.carts);
    this.updateBlobs();
    this.world.flush();
    this.updateBeacon(dt);
    this.fx.update(dt);
    this.updateCamera(dt);
    this.updateOverlays();
  }

  updatePlay(dt, move) {
    const r = this.round;
    const input = this.input;
    r.elapsed += dt;
    // memoria
    if (r.level.memory) {
      if (r.memLeft > 0) {
        r.memLeft -= dt;
        this.ui.setMemo(r.memLeft / r.level.memory);
        if (r.memLeft <= 0) {
          this.ui.cover(true);
          this.ui.toast('¡La lista se escondió!', 'soft', '¿Recuerdas qué comprar?', 1800);
          this.audio.whoosh();
        }
      } else if (r.peekLeft > 0) {
        r.peekLeft -= dt;
        this.ui.setMemo(r.peekLeft / 3);
        if (r.peekLeft <= 0) this.ui.cover(true);
      }
    }
    if (!r.calm) this.ui.setTimer(true, r.level.time - r.elapsed, (r.level.time - r.elapsed) / r.level.time);
    // jugador
    const others = this.otherCircles();
    this.player.update(dt, move, input.run, this.world.colliders, others);
    this.audio.setRattle(this.player.speed);
    // objetivo: columna cercana o bajo el puntero
    const near = this.nearestColumn();
    if (this.pointer.inside && this.pointer.moved && !this.input.touchMode) {
      this.pointer.moved = false;
      this.hover = this.pickColumnAt(this.pointer.x, this.pointer.y);
    }
    const hoverNear = this.hover && this.inReach(this.hover, 2.4);
    const tgt = hoverNear ? this.hover : near;
    this.target = tgt;
    this.bubbleCol = tgt || this.hover;
    this.bubbleNear = !!tgt;
    const atPad = this.atCheckout();
    if (input.take('action')) {
      if (atPad && !tgt) this.tryCheckout();
      else if (tgt) this.pick(tgt);
      else if (atPad) this.tryCheckout();
      else {
        this.player.char.bounce(0.06);
      }
    }
    if (input.take('pause')) this.pause();
    if (input.take('back')) this.returnLast();
    if (input.take('peek')) this.peek();
    this.ui.setAction(atPad && !tgt ? 'Pagar' : 'Tomar', atPad && !tgt ? 'pay' : tgt ? 'ready' : 'idle');
    // meneo de la columna señalada
    if (tgt !== this.prevTarget) {
      this.resetWiggle();
      this.prevTarget = tgt;
    }
    const W = this.world;
    if (tgt) {
      const amp = this.options.reduced ? 0.35 : 1;
      let i = 0;
      let first = null;
      for (const s of tgt.slots) {
        if (s.taken) continue;
        if (!first) first = s;
        const ph = this.time * 9 + i * 1.3;
        const wig = Math.sin(ph) * 0.07 * amp;
        const hop = Math.max(0, Math.sin(ph * 0.5)) * 0.025 * amp;
        W.setSlot(s, W.slotMatrix(s, wig, hop, 1, _m));
        i++;
      }
      if (first) {
        const ph = this.time * 9;
        W.slotMatrix(first, Math.sin(ph) * 0.07 * amp, Math.max(0, Math.sin(ph * 0.5)) * 0.025 * amp, 1.06, _m);
        W.outline.geometry = W.geoms[tgt.productId];
        _m.decompose(W.outline.position, W.outline.quaternion, W.outline.scale);
        W.outline.scale.multiplyScalar(1.07);
        W.outline.visible = true;
      } else W.outline.visible = false;
    } else W.outline.visible = false;
    // pista
    if (this.hint) {
      this.hint.t -= dt;
      if (this.hint.t <= 0) this.hint = null;
    }
  }

  otherCircles() {
    if (!this._others) this._others = [];
    const o = this._others;
    o.length = 0;
    for (const s of this.shoppers) {
      if (!s.active) continue;
      if (!s._c) s._c = [{ x: 0, z: 0, r: 0.34 }, { x: 0, z: 0, r: 0.42 }];
      s._c[0].x = s.pos.x;
      s._c[0].z = s.pos.y;
      s._c[1].x = s.pos.x + Math.sin(s.heading) * 0.7;
      s._c[1].z = s.pos.y + Math.cos(s.heading) * 0.7;
      o.push(s._c[0], s._c[1]);
    }
    // la cajera y el mostrador ya son colisionadores fijos
    return o;
  }

  cartJiggleUpdate(dt) {
    if (!this.cartJiggle) {
      this.cartJiggle = { x: 0, z: 0, sx: new Spring(0, 11, 0.25), sz: new Spring(0, 11, 0.25) };
    }
    const j = this.cartJiggle;
    const p = this.player;
    // fuerza lateral (curvas) y longitudinal (acelerar/frenar)
    j.sx.target = clamp(p.angVel * p.speed * 0.08, -1, 1);
    j.sz.target = clamp(-p.fwdAccel * 0.06, -1, 1);
    j.x = j.sx.step(dt);
    j.z = j.sz.step(dt);
  }

  updateFlying(dt) {
    const W = this.world;
    for (let i = this.flying.length - 1; i >= 0; i--) {
      const it = this.flying[i];
      it.t += dt / it.dur;
      const k = Math.min(1, it.t);
      if (it.state === 'fly') {
        // arco hacia el hueco del carrito (que se mueve): se interpola contra su posición actual
        this.itemWorldMatrix(it, _m);
        _m.decompose(_v2, _q, _s);
        const e = easeInOutCubic(k);
        _v.lerpVectors(it.from, _v2, e);
        _v.y += Math.sin(k * Math.PI) * (0.8 + it.from.distanceTo(_v2) * 0.12);
        const spin = (1 - e) * Math.PI * 2;
        _e.set(0, it.fromRot + spin, 0);
        _q2.copy(_q);
        _q.setFromEuler(_e).slerp(_q2, e);
        const sc = lerp(1, 0.74, e) * (1 + Math.sin(k * Math.PI) * 0.15);
        _s.setScalar(sc);
        _m.compose(_v, _q, _s);
        W.setSlot(it.slot, _m);
        if (k >= 1) {
          it.state = 'in';
          it.squash.x = 0.6;
          it.squash.v = 0;
          this.flying.splice(i, 1);
          this.audio.land(it.cartSlot % 4);
          this.player.cart.bump.v += 0.6;
          if (!it.wrong) {
            this.audio.good();
            this.fx.sparkle(_v2.x, _v2.y + 0.2, _v2.z, 0xfff3a0, 8);
          }
        }
      } else if (it.state === 'back') {
        const e = easeInOutCubic(k);
        _v.lerpVectors(it.from, it.slot.pos, e);
        _v.y += Math.sin(k * Math.PI) * (0.6 + it.from.distanceTo(it.slot.pos) * 0.1);
        _e.set(0, it.slot.rotY + (1 - e) * Math.PI * 2, 0);
        _q.setFromEuler(_e);
        _s.setScalar(lerp(0.74, 1, e));
        _m.compose(_v, _q, _s);
        W.setSlot(it.slot, _m);
        if (k >= 1) {
          this.flying.splice(i, 1);
          W.shelveSlot(it.slot);
          this.audio.land(1);
        }
      }
    }
  }

  updateCartItems(dt) {
    const W = this.world;
    for (const it of this.cartItems) {
      if (it.state !== 'in') continue;
      it.squash.step(dt);
      this.itemWorldMatrix(it, _m);
      W.setSlot(it.slot, _m);
    }
  }

  cashierUpdate(dt) {
    const c = this.cashier;
    // mira al jugador cuando está cerca
    const dx = this.player.pos.x - c.root.position.x;
    const dz = this.player.pos.y - c.root.position.z;
    const d = Math.hypot(dx, dz);
    if (this.state === 'play' || this.state === 'title' || this.state === 'brief') {
      const a = angleDiff(c.root.rotation.y, Math.atan2(dx, dz));
      c.lookYaw = d < 7 ? clamp(a, -0.9, 0.9) : 0;
    }
    c.update(dt, 0, 0, 0);
  }

  updateBlobs() {
    const list = this._blobs || (this._blobs = []);
    const pool = this._blobPool || (this._blobPool = Array.from({ length: 12 }, () => ({})));
    list.length = 0;
    const add = (x, z, sx, sz, rot) => {
      const b = pool[list.length];
      b.x = x;
      b.z = z;
      b.sx = sx;
      b.sz = sz;
      b.rot = rot;
      list.push(b);
    };
    const p = this.player;
    add(p.pos.x, p.pos.y, 0.9, 0.9, 0);
    add(p.cartWorld.x, p.cartWorld.y, 1.05, 0.85, p.heading);
    for (const s of this.shoppers) {
      if (!s.active) continue;
      add(s.pos.x, s.pos.y, 0.95, 0.95, 0);
      add(s.pos.x + Math.sin(s.heading) * 0.7, s.pos.y + Math.cos(s.heading) * 0.7, 1.05, 0.85, s.heading);
    }
    add(this.cashier.root.position.x, this.cashier.root.position.z, 0.9, 0.9, 0);
    this.world.setBlobs(list);
  }

  updateBeacon(dt) {
    const W = this.world;
    if (W.beacon.visible) {
      const t = this.time;
      W.beaconArrow.position.y = 2.0 + Math.sin(t * 3.2) * 0.18;
      W.beaconArrow.rotation.y = t * 1.6;
      W.beaconRing.rotation.y = t * 0.6;
      const s = 1 + Math.sin(t * 4) * 0.06;
      W.beaconRing.scale.set(s, 1, s);
    }
    // pista: flecha amarilla sobre la cabeza que apunta al objetivo
    const h = this.hint;
    const arrow = this.hintArrow;
    if (h && this.state === 'play') {
      const p = this.player;
      const dx = h.x - p.pos.x;
      const dz = h.z - p.pos.y;
      arrow.visible = Math.hypot(dx, dz) > 1.2;
      arrow.position.set(p.pos.x + Math.sin(Math.atan2(dx, dz)) * 0.9, 1.75 + Math.sin(this.time * 6) * 0.06, p.pos.y + Math.cos(Math.atan2(dx, dz)) * 0.9);
      arrow.rotation.set(0, Math.atan2(dx, dz), 0);
      if (h.col) {
        W.hintRing.visible = true;
        W.hintRing.position.set(h.col.x, 0.03, h.col.front + 0.55);
        const s = 1 + Math.sin(this.time * 6) * 0.08;
        W.hintRing.scale.set(s, 1, s);
      }
    } else {
      arrow.visible = false;
      W.hintRing.visible = false;
    }
  }

  /* ================================================================ cámara */

  updateCamera(dt) {
    const c = this.cam;
    const cam = this.camera;
    const aspect = cam.aspect;
    const portrait = aspect < 1;
    const p = this.player;
    let px;
    let py;
    let pz;
    let lx;
    let ly;
    let lz;
    if (c.mode === 'title') {
      c.orbit += dt * (this.options.reduced ? 0.03 : 0.07);
      const a = Math.sin(c.orbit) * 0.42;
      const R = portrait ? 21 : 17.5;
      lx = -1.2;
      ly = portrait ? -6 : 0.2;
      lz = -1.6;
      px = lx + Math.sin(a) * R;
      py = portrait ? 19.5 : 13.5;
      pz = lz + Math.cos(a) * R;
    } else if (c.mode === 'play') {
      const f = portrait ? clamp(Math.pow(1.0 / aspect, 0.42), 1, 1.5) : aspect < 1.4 ? 1.1 : 1;
      const look = this.options.reduced ? 0.2 : 0.42;
      lx = p.pos.x + p.vel.x * look;
      ly = 0.6;
      lz = p.pos.y + p.vel.y * look - 0.15;
      px = lx;
      py = ly + 8.0 * f;
      pz = lz + 7.6 * f;
    } else {
      // caja y celebración: vista de la cinta, la cajera y el niño
      const W = this.world;
      lx = CHECKOUT.counterX - 0.6;
      ly = 0.95;
      lz = (CHECKOUT.z0 + W.scanZ) / 2 + 0.2;
      if (portrait) {
        px = lx - 1.6;
        py = 6.2;
        pz = lz + 7.6;
      } else {
        px = lx - 3.2;
        py = 3.6;
        pz = lz + 5.4;
      }
      if (c.mode === 'win') {
        // el niño queda a un lado (escritorio) o arriba (celular) de la tarjeta de victoria
        lx = p.pos.x + (portrait ? 0.3 : 2.0);
        lz = p.pos.y + (portrait ? 1.6 : 0.6);
        ly = portrait ? 0.0 : 0.9;
        px = lx - (portrait ? 0.8 : 2.4);
        py = portrait ? 5.4 : 3.2;
        pz = lz + (portrait ? 5.6 : 5.0);
      }
    }
    c.px.target = px;
    c.py.target = py;
    c.pz.target = pz;
    c.lx.target = lx;
    c.ly.target = ly;
    c.lz.target = lz;
    if (!c.init) {
      c.init = true;
      c.px.snap(px);
      c.py.snap(py);
      c.pz.snap(pz);
      c.lx.snap(lx);
      c.ly.snap(ly);
      c.lz.snap(lz);
    }
    cam.position.set(c.px.step(dt), c.py.step(dt), c.pz.step(dt));
    _v.set(c.lx.step(dt), c.ly.step(dt), c.lz.step(dt));
    if (this.shake > 0.001) {
      this.shake *= Math.exp(-10 * dt);
      cam.position.x += (Math.random() - 0.5) * this.shake;
      cam.position.y += (Math.random() - 0.5) * this.shake;
    }
    cam.lookAt(_v);
    // sombra: la cámara de luz sigue al foco (ajustada a texel para no titilar)
    const L = this.sun;
    const tx = Math.round(_v.x * 4) / 4;
    const tz = Math.round(_v.z * 4) / 4;
    L.target.position.set(tx, 0, tz);
    L.position.set(tx - 7, 15, tz + 6);
  }

  /* ================================================================ burbujas sobre el mundo */

  project(x, y, z, out) {
    _v.set(x, y, z).project(this.camera);
    const r = this.renderer.domElement;
    out.x = ((_v.x + 1) / 2) * r.clientWidth;
    out.y = ((1 - _v.y) / 2) * r.clientHeight;
    out.vis = _v.z < 1;
    return out;
  }

  updateOverlays() {
    const pt = this._pt || (this._pt = { x: 0, y: 0, vis: false });
    if (this.state === 'play' && this.bubbleCol) {
      const col = this.bubbleCol;
      this.project(col.x, col.top + 0.15, col.front - 0.15, pt);
      const ei = this.entryFor(col.product);
      const needed = ei >= 0 && this.round.list[ei].got < this.round.list[ei].qty && !(this.round.level.memory && this.round.memLeft <= 0 && this.round.peekLeft <= 0);
      if (pt.vis) this.ui.showBubble(pt.x, pt.y, col.product, this.bubbleNear, needed, 'E');
      else this.ui.hideBubble();
    } else this.ui.hideBubble();
    // globito de los clientes
    let said = false;
    if (this.state === 'play') {
      for (const s of this.shoppers) {
        if (!s.active || s.sayT <= 0) continue;
        this.project(s.pos.x, 1.75, s.pos.y, pt);
        if (pt.vis) {
          this.ui.npcSay(s.say, pt.x, pt.y);
          said = true;
        }
        break;
      }
    }
    if (!said) this.ui.npcSay(null);
  }

  /* ================================================================ pruebas automáticas */

  exposeDebug() {
    const g = this;
    const waitState = (s, ms = 20000) =>
      new Promise((res, rej) => {
        const t0 = performance.now();
        const loop = () => {
          if (g.state === s) return res(true);
          if (performance.now() - t0 > ms) return rej(new Error('timeout esperando ' + s + ' (estado ' + g.state + ')'));
          setTimeout(loop, 50);
        };
        loop();
      });
    window.MarketDebug = {
      state: () => ({
        state: g.state,
        level: g.round ? g.round.level.n : 0,
        list: g.round ? g.round.list.map((e) => ({ ...e })) : [],
        budget: g.round ? g.round.budget : 0,
        cart: g.cartItems.map((it) => ({ key: it.key, id: it.product.id, wrong: it.wrong, state: it.state })),
        cartTotal: g.cartTotal(),
        player: { x: g.player.pos.x, z: g.player.pos.y },
        stats: { ...g.stats },
        drawCalls: g.renderer.info.render.calls,
        triangles: g.renderer.info.render.triangles,
      }),
      startLevel: (n, seed = 12345) => {
        g.audio.unlock();
        g.openBrief(n, { seed });
        g.beginPlay();
        return window.MarketDebug.state();
      },
      /** Toma una unidad del producto (por id) como si el jugador estuviera enfrente. */
      pick: (productId) => {
        const col = g.world.columns.find((c) => c.productId === productId);
        if (!col) return false;
        g.player.place(col.x, col.front + 1.3, Math.PI);
        return g.pick(col);
      },
      /** Ids de productos que cumplen la lista (uno por unidad requerida). */
      needed: () => {
        const out = [];
        for (const e of g.round.list) {
          const p = productsOfCat(e.cat).sort((a, b) => a.price - b.price)[0];
          for (let i = e.got; i < e.qty; i++) out.push(p.id);
        }
        return out;
      },
      returnItem: (productId) => {
        const it = g.cartItems.find((x) => x.product.id === productId && x.state === 'in');
        if (!it) return false;
        g.returnItem(it.key);
        return true;
      },
      settle: () => new Promise((res) => {
        const loop = () => (g.flying.length ? setTimeout(loop, 50) : res(true));
        loop();
      }),
      goToCheckout: async (force = true) => {
        await window.MarketDebug.settle();
        g.player.place(CHECKOUT.padX, CHECKOUT.padZ, Math.PI);
        g.tryCheckout(force);
        g.tw.scale = 8; // en pruebas la cinta va rápido
        await waitState('pay', 180000);
        await new Promise((r) => setTimeout(r, 400));
        return { total: g.round.total, wallet: [...document.querySelectorAll('#wallet .money-el')].map((e) => +e.dataset.v) };
      },
      pay: async (amounts) => {
        g.payment.debugPay(amounts);
        await waitState('win', 120000);
        return window.MarketDebug.result();
      },
      waitState,
      teleport: (x, z, h = Math.PI) => g.player.place(x, z, h),
      result: () => g.result(),
      exit: () => g.exitGame(),
      toMenu: () => g.toMenu(),
      setOption: (k, v) => {
        g.options[k] = v;
        g.applyOptions();
      },
      game: g,
    };
  }
}

const IDQ = new THREE.Quaternion();
