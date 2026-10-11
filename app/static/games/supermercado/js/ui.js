/*
 * Interfaz DOM: pantallas, lista de compras, carrito, burbujas y avisos.
 * Nunca muestra KPIs ni puntajes clínicos: solo lista, carrito, dinero y estrellas.
 */
import { LEVELS, catName, soles, productsOfCat } from './config.js';

const $ = (id) => document.getElementById(id);

const svg = (id, cls = '') => `<svg class="${cls}"><use href="#${id}"/></svg>`;

export class UI {
  constructor() {
    this.icons = {};
    this.current = 'scrLoading';
    this.stack = [];
    this.toastT = null;
    this.onReturn = null;
    this.listEl = $('listItems');
    this.chipsEl = $('cartChips');
    this.bubble = $('bubble');
    this.npc = $('npcBubble');
    this.bubbleShown = false;
    this.lastBubbleKey = '';
    document.querySelectorAll('[data-back]').forEach((b) => b.addEventListener('click', () => this.back()));
  }

  /* ------------------------------------------------ pantallas */

  show(id, { push = true } = {}) {
    if (this.current === id) return;
    if (push && this.current) this.stack.push(this.current);
    if (this.current) $(this.current).classList.remove('show');
    this.current = id;
    if (id) {
      $(id).classList.add('show');
      const f = $(id).querySelector('.btn.big, .btn');
      if (f && !matchMedia('(pointer: coarse)').matches) setTimeout(() => f.focus({ preventScroll: true }), 60);
    }
  }

  hideAll() {
    if (this.current) $(this.current).classList.remove('show');
    this.current = null;
    this.stack.length = 0;
  }

  back() {
    const prev = this.stack.pop();
    if (this.onBack && this.onBack(this.current, prev)) return;
    this.show(prev || 'scrTitle', { push: false });
  }

  hud(on) {
    $('hud').classList.toggle('hidden', !on);
    $('touch').classList.toggle('hidden', !on || !document.body.classList.contains('touchUI'));
  }

  setTouch(on) {
    document.body.classList.toggle('touchUI', on);
    const hudOn = !$('hud').classList.contains('hidden');
    $('touch').classList.toggle('hidden', !on || !hudOn);
  }

  /* ------------------------------------------------ niveles */

  renderLevels(progress, onPick) {
    const grid = $('levelGrid');
    grid.innerHTML = '';
    const colors = ['#95e7ff', '#ffd28f', '#d389ff', '#8fc4b8', '#ff9fb2', '#f5c84b'];
    LEVELS.forEach((L, i) => {
      const locked = L.n > progress.unlocked;
      const stars = progress.stars[L.n] || 0;
      const feats = [];
      feats.push(`${L.items} cosas`);
      if (L.memory) feats.push('memoria');
      if (L.budget) feats.push('presupuesto');
      if (L.pay === 'change') feats.push('vuelto');
      if (L.npcs > 1) feats.push('gente');
      const b = document.createElement('button');
      b.className = 'lvl' + (locked ? ' locked' : '');
      b.innerHTML = `<span class="num" style="background:${colors[i]}">${L.n}</span><b>${L.name}</b><small>${L.goal}</small>
        <span class="feat">${feats.map((f) => `<span>${f}</span>`).join('')}</span>
        <span class="st">${[1, 2, 3].map((k) => svg('i-star', k <= stars ? 'on' : '')).join('')}</span>
        ${locked ? svg('i-lock', 'lockI') : ''}`;
      b.addEventListener('click', () => {
        if (locked) {
          this.toast('Completa el nivel anterior para abrir este', 'soft');
          b.animate([{ transform: 'translateX(-5px)' }, { transform: 'translateX(5px)' }, { transform: 'none' }], { duration: 300 });
          return;
        }
        onPick(L.n);
      });
      grid.appendChild(b);
    });
  }

  renderBrief(L, round) {
    $('briefNum').textContent = L.n;
    $('briefName').textContent = L.name;
    $('briefGoal').textContent = L.goal;
    const list = $('briefList');
    list.innerHTML = round.list
      .map((e) => `<span class="it"><img src="${this.catIcon(e.cat)}" alt=""><span class="q">${e.qty}</span>${catName(e.cat, e.qty)}</span>`)
      .join('');
    const notes = [];
    if (L.memory) notes.push(`${svg('i-eye')}La lista se esconde en ${L.memory} segundos. ¡Memorízala!`);
    if (round.budget) notes.push(`${svg('i-coin')}Tienes ${soles(round.budget)}. Mira los precios y no te pases.`);
    if (L.pay === 'change') notes.push(`${svg('i-coin')}En la caja te preguntarán cuánto vuelto recibes.`);
    if (L.npcs > 1) notes.push(`${svg('i-cart')}Hay más clientes comprando. ¡Esquívalos!`);
    if (!round.calm && L.time) notes.push(`${svg('i-clock')}Termina en ${Math.floor(L.time / 60)}:${String(L.time % 60).padStart(2, '0')} para ganar una estrella extra.`);
    $('briefNotes').innerHTML = notes.map((n) => `<div class="note-line">${n}</div>`).join('');
  }

  catIcon(cat) {
    const p = productsOfCat(cat);
    // con variantes se usa la versión más barata como ícono genérico
    const pick = p.slice().sort((a, b) => a.price - b.price)[0];
    return this.icons[pick.id] || '';
  }

  /* ------------------------------------------------ lista */

  setList(list, memo) {
    this.listEl.innerHTML = list
      .map(
        (e, i) => `<li data-i="${i}"><span class="bx">${svg('i-check')}</span><img src="${this.catIcon(e.cat)}" alt=""><span class="nm">${catName(e.cat, e.qty)}${
          productsOfCat(e.cat).length > 1 ? '<span class="any">elige</span>' : ''
        }</span><span class="ct">${e.got}/${e.qty}</span></li>`,
      )
      .join('');
    $('listCard').classList.toggle('memo', !!memo);
    $('listCard').classList.remove('covered');
    this.updateList(list, -1);
  }

  updateList(list, popIndex) {
    let done = 0;
    let total = 0;
    list.forEach((e, i) => {
      const li = this.listEl.children[i];
      if (!li) return;
      li.classList.toggle('done', e.got >= e.qty);
      li.querySelector('.ct').textContent = `${e.got}/${e.qty}`;
      if (i === popIndex) {
        li.classList.remove('pop');
        void li.offsetWidth;
        li.classList.add('pop');
      }
      done += Math.min(e.got, e.qty);
      total += e.qty;
    });
    $('listCount').textContent = `${done}/${total}`;
    $('memDone').textContent = `Llevas ${done} de ${total}`;
  }

  setMemo(frac) {
    $('memBar').firstElementChild.style.transform = `scaleX(${Math.max(0, frac)})`;
  }

  cover(on) {
    $('listCard').classList.toggle('covered', on);
  }

  /* ------------------------------------------------ carrito */

  setCart(items, showTotal, total) {
    const el = this.chipsEl;
    // reconstrucción incremental: se agregan solo las nuevas fichas
    const keys = items.map((it) => it.key);
    [...el.children].forEach((c) => {
      if (!keys.includes(+c.dataset.key) && !c.classList.contains('out')) {
        c.classList.add('out');
        setTimeout(() => c.remove(), 300);
      }
    });
    items.forEach((it) => {
      let c = el.querySelector(`[data-key="${it.key}"]`);
      if (!c) {
        c = document.createElement('button');
        c.className = 'chip';
        c.dataset.key = it.key;
        c.title = `${it.product.name} · toca para devolver`;
        c.innerHTML = `<img src="${this.icons[it.product.id] || ''}" alt="${it.product.name}"><span class="ret">${svg('i-back')}</span>`;
        c.addEventListener('click', () => this.onReturn && this.onReturn(+c.dataset.key));
        el.appendChild(c);
        el.scrollLeft = el.scrollWidth;
      }
      c.classList.toggle('wrong', !!it.wrong);
    });
    $('cartCount').textContent = items.length;
    const ic = document.querySelector('.cartIcon');
    ic.classList.remove('bump');
    void ic.offsetWidth;
    ic.classList.add('bump');
    const t = $('cartTotal');
    t.classList.toggle('hidden', !showTotal);
    if (showTotal) t.textContent = soles(total);
  }

  /** En táctil la barra del carrito va debajo de los botones de arriba (que pueden ocupar dos filas). */
  layoutTop() {
    const tr = $('topRight').getBoundingClientRect();
    document.documentElement.style.setProperty('--cartTop', `${Math.round(tr.bottom + 8)}px`);
  }

  setBudget(budget, spent) {
    const pill = $('budgetPill');
    const was = pill.classList.contains('hidden');
    pill.classList.toggle('hidden', !budget);
    if (was === !!budget || !this._laid) {
      this._laid = true;
      requestAnimationFrame(() => this.layoutTop());
    }
    if (!budget) return;
    const left = budget - spent;
    $('budgetText').innerHTML = left >= 0 ? `${soles(left)} <span class="sub">te quedan</span>` : `${soles(-left)} <span class="sub">te pasaste</span>`;
    const over = left < 0;
    if (over && !pill.classList.contains('over')) pill.classList.add('over');
    if (!over) pill.classList.remove('over');
  }

  setTimer(on, left, frac) {
    const p = $('timerPill');
    p.classList.toggle('hidden', !on);
    if (!on) return;
    const s = Math.max(0, Math.ceil(left));
    const txt = `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
    if (this._tt !== txt) {
      $('timerText').textContent = txt;
      this._tt = txt;
    }
    $('timerRing').style.strokeDashoffset = String(94.25 * (1 - Math.max(0, frac)));
    p.classList.toggle('late', frac < 0.25);
  }

  goPay(on) {
    $('goPay').classList.toggle('hidden', !on);
  }

  /* ------------------------------------------------ burbujas */

  showBubble(x, y, p, near, needed, keyLabel) {
    const b = this.bubble;
    const key = p.id + near + needed + keyLabel;
    if (key !== this.lastBubbleKey) {
      this.lastBubbleKey = key;
      $('bubbleImg').src = this.icons[p.id] || '';
      $('bubbleName').textContent = p.name;
      $('bubblePrice').textContent = soles(p.price);
      $('bubbleKey').textContent = keyLabel;
      b.classList.toggle('far', !near);
      b.classList.toggle('need', needed);
    }
    if (!this.bubbleShown) {
      b.classList.remove('hidden');
      this.bubbleShown = true;
    }
    const w = b.offsetWidth;
    const h = b.offsetHeight;
    b.style.transform = `translate(${Math.round(x - w / 2)}px, ${Math.round(y - h - 14)}px)`;
  }

  hideBubble() {
    if (!this.bubbleShown) return;
    this.bubble.classList.add('hidden');
    this.bubbleShown = false;
    this.lastBubbleKey = '';
  }

  npcSay(text, x, y) {
    const n = this.npc;
    if (!text) {
      n.classList.add('hidden');
      return;
    }
    if (n.textContent !== text) n.textContent = text;
    n.classList.remove('hidden');
    n.style.transform = `translate(${Math.round(x - n.offsetWidth / 2)}px, ${Math.round(y - n.offsetHeight - 6)}px)`;
  }

  toast(text, kind = '', sub = '', ms = 2200) {
    const t = $('toast');
    t.className = 'toast ' + kind;
    t.innerHTML = text + (sub ? `<small>${sub}</small>` : '');
    void t.offsetWidth;
    t.classList.add('show');
    clearTimeout(this.toastT);
    this.toastT = setTimeout(() => t.classList.remove('show'), ms);
  }

  setAction(label, state) {
    $('actLabel').textContent = label;
    const a = $('actBtn');
    a.classList.toggle('ready', state === 'ready');
    a.classList.toggle('pay', state === 'pay');
    a.classList.toggle('idle', state === 'idle');
  }

  /* ------------------------------------------------ diálogos */

  dialog(title, text, buttons) {
    return new Promise((res) => {
      $('dlgTitle').textContent = title;
      $('dlgText').innerHTML = text;
      const row = $('dlgBtns');
      row.innerHTML = '';
      buttons.forEach((b, i) => {
        const el = document.createElement('button');
        el.className = 'btn ' + (b.cls || (i === buttons.length - 1 ? 'big' : 'ghost'));
        el.textContent = b.label;
        el.addEventListener('click', () => {
          this.show(null, { push: false });
          res(b.value);
        });
        row.appendChild(el);
      });
      this.show('scrDialog', { push: false });
    });
  }

  /* ------------------------------------------------ victoria */

  renderWin(sum) {
    $('winTitle').textContent = sum.title;
    const st = $('winStars');
    st.classList.remove('show');
    [...st.children].forEach((s, i) => s.classList.toggle('on', i < sum.stars));
    setTimeout(() => st.classList.add('show'), 250);
    [...st.children].forEach((s, i) => (s.style.transitionDelay = `${0.3 + i * 0.22}s`));
    $('winLines').innerHTML = sum.lines
      .map((l, i) => `<div class="winLine ${l.big ? 'big' : ''}" style="animation-delay:${0.5 + i * 0.12}s"><span>${l.k}</span><span>${l.v}</span></div>`)
      .join('');
    $('btnWinNext').classList.toggle('hidden', !sum.hasNext);
  }
}
