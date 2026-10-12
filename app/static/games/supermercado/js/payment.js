/*
 * Minijuego de pago con monedas y billetes peruanos.
 * Arrastrar (o tocar) el dinero a la bandeja, pagar, y en niveles altos calcular el vuelto.
 */
import { MONEY, soles } from './config.js';
import { shuffle } from './util.js';

const $ = (id) => document.getElementById(id);
const MONEY_BY_V = Object.fromEntries(MONEY.map((m) => [m.v, m]));

export class Payment {
  constructor(audio) {
    this.audio = audio;
    this.wallet = $('wallet');
    this.tray = $('tray');
    this.trayItems = $('trayItems');
    this.active = false;
    this.mistakes = 0;
    this.drag = null;
    $('btnPay').addEventListener('click', () => this.pay());
    $('btnClearTray').addEventListener('click', () => {
      [...this.trayItems.children].forEach((el) => this.move(el, this.wallet));
      this.refresh();
    });
  }

  /**
   * opts: { items:[{name, price, icon, aside}], total, wallet:[cents], mode:'exact'|'auto'|'change' }
   * Devuelve una promesa con { paid, change, mistakes }.
   */
  open(opts) {
    this.opts = opts;
    this.mistakes = 0;
    this.short = 0;
    this.active = true;
    this.answered = false;
    $('payTotal').textContent = soles(opts.total);
    $('rcItems').innerHTML = opts.items
      .map((it, i) => `<li class="${it.aside ? 'aside' : ''}" style="animation-delay:${i * 0.05}s"><img src="${it.icon}" alt=""><span>${it.name}</span><b>${it.aside ? '—' : soles(it.price)}</b></li>`)
      .join('');
    this.wallet.innerHTML = '';
    this.trayItems.innerHTML = '';
    opts.wallet
      .slice()
      .sort((a, b) => b - a)
      .forEach((v, i) => {
        const el = this.makeMoney(v);
        el.style.animation = `chipIn .45s cubic-bezier(.34,1.56,.64,1) ${i * 0.04}s both`;
        this.wallet.appendChild(el);
      });
    $('changeBox').classList.add('hidden');
    $('btnPay').disabled = false;
    $('btnClearTray').disabled = false;
    $('payAsk').textContent = opts.mode === 'exact' ? 'Paga el total justo con tus monedas' : 'Arrastra o toca el dinero para pagar';
    this.refresh();
    return new Promise((res) => (this.resolve = res));
  }

  makeMoney(v) {
    const m = MONEY_BY_V[v];
    const el = document.createElement('button');
    el.className = 'money-el ' + (m.kind === 'coin' ? `coin ${m.metal}` : `bill ${m.color}`);
    el.dataset.v = v;
    el.setAttribute('aria-label', soles(v));
    if (m.kind === 'coin') {
      el.style.width = el.style.height = m.size + 'px';
      el.innerHTML = `<span><span class="v">${m.label}</span>${m.unit ? `<span class="u">${m.unit}</span>` : ''}</span>`;
    } else {
      el.innerHTML = `<span class="v">${m.label}</span><span class="u">${m.unit}</span>`;
    }
    el.addEventListener('pointerdown', (e) => this.down(e, el));
    el.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        e.stopPropagation();
        this.toggle(el);
      }
    });
    return el;
  }

  down(e, el) {
    if (!this.active || this.answered) return;
    e.preventDefault();
    el.setPointerCapture(e.pointerId);
    const d = { el, id: e.pointerId, x0: e.clientX, y0: e.clientY, moved: false };
    this.drag = d;
    const move = (ev) => {
      if (ev.pointerId !== d.id) return;
      const dx = ev.clientX - d.x0;
      const dy = ev.clientY - d.y0;
      if (!d.moved && Math.hypot(dx, dy) > 7) {
        d.moved = true;
        el.classList.add('dragging');
      }
      if (d.moved) {
        el.style.transform = `translate(${dx}px, ${dy}px) rotate(${dx * 0.04}deg) scale(1.08)`;
        const r = this.tray.getBoundingClientRect();
        const over = ev.clientX > r.left && ev.clientX < r.right && ev.clientY > r.top && ev.clientY < r.bottom;
        this.tray.classList.toggle('hot', over && el.parentElement === this.wallet);
      }
    };
    const up = (ev) => {
      if (ev.pointerId !== d.id) return;
      el.removeEventListener('pointermove', move);
      el.removeEventListener('pointerup', up);
      el.removeEventListener('pointercancel', up);
      this.tray.classList.remove('hot');
      el.classList.remove('dragging');
      this.drag = null;
      if (!d.moved) {
        el.style.transform = '';
        this.toggle(el);
        return;
      }
      const r = this.tray.getBoundingClientRect();
      const over = ev.clientX > r.left && ev.clientX < r.right && ev.clientY > r.top && ev.clientY < r.bottom;
      const target = over ? this.trayItems : this.wallet;
      if (target !== el.parentElement) this.move(el, target, true);
      else {
        el.style.transform = '';
      }
      this.refresh();
    };
    el.addEventListener('pointermove', move);
    el.addEventListener('pointerup', up);
    el.addEventListener('pointercancel', up);
  }

  toggle(el) {
    if (!this.active || this.answered) return;
    this.move(el, el.parentElement === this.wallet ? this.trayItems : this.wallet);
    this.refresh();
  }

  /** Mueve un billete/moneda entre contenedores con animación FLIP (sale desde donde estaba). */
  move(el, target, fromDrag = false) {
    const before = el.getBoundingClientRect();
    target.appendChild(el);
    const after = el.getBoundingClientRect();
    const dx = before.left - after.left;
    const dy = before.top - after.top;
    el.style.transition = 'none';
    el.style.transform = `translate(${dx}px, ${dy}px)${fromDrag ? ' scale(1.08)' : ''}`;
    void el.offsetWidth;
    el.style.transition = '';
    el.style.transform = '';
    const v = +el.dataset.v;
    if (target === this.trayItems) {
      if (v >= 1000) this.audio.bill();
      else this.audio.coin(Math.log2(v / 10));
    } else this.audio.click();
  }

  sum() {
    let s = 0;
    for (const el of this.trayItems.children) s += +el.dataset.v;
    return s;
  }

  refresh() {
    const s = this.sum();
    $('traySum').textContent = soles(s);
    const need = this.opts.total - s;
    const n = $('trayNeed');
    if (s === 0) {
      n.textContent = '';
    } else if (need > 0) {
      n.textContent = `Falta ${soles(need)}`;
      n.className = 'need';
    } else {
      n.textContent = need === 0 ? '¡Justo!' : '¡Alcanza!';
      n.className = 'need ok';
    }
    this.tray.querySelector('.trayHint').style.opacity = s ? 0 : 1;
  }

  pay() {
    if (!this.active || this.answered) return;
    const s = this.sum();
    const total = this.opts.total;
    if (s < total) {
      // tocar «Pagar» para explorar no cuenta; desde el segundo intento corto, sí
      this.short++;
      if (this.short >= 2) this.mistakes++;
      this.audio.soft();
      this.tray.classList.remove('shake');
      void this.tray.offsetWidth;
      this.tray.classList.add('shake');
      $('payAsk').textContent = s === 0 ? 'Pon dinero en la bandeja' : `Todavía falta ${soles(total - s)}. ¡Agrega un poco más!`;
      return;
    }
    const change = s - total;
    if (this.opts.mode === 'exact' && change > 0) {
      // en el primer nivel se practica pagar justo: se pide con cariño, sin contar error
      this.audio.soft();
      this.tray.classList.remove('shake');
      void this.tray.offsetWidth;
      this.tray.classList.add('shake');
      $('payAsk').textContent = `Pusiste ${soles(change)} de más. ¿Puedes pagar justo ${soles(total)}?`;
      return;
    }
    this.answered = true;
    $('btnPay').disabled = true;
    $('btnClearTray').disabled = true;
    if (this.opts.mode === 'change' && change > 0) {
      this.askChange(s, change);
      return;
    }
    this.finish(s, change);
  }

  askChange(paid, change) {
    const box = $('changeBox');
    box.classList.remove('hidden');
    $('changeQ').innerHTML = `Pagaste <b>${soles(paid)}</b> y la cuenta es <b>${soles(this.opts.total)}</b>.<br>¿Cuánto vuelto te deben dar?`;
    const step = change % 100 === 0 ? 100 : change % 50 === 0 ? 50 : 10;
    const cands = [change + step, change - step, change + step * 2, change + 100, change - 100, change + 50].filter((c) => c > 0 && c !== change);
    const uniq = [...new Set(cands)].slice(0, 2);
    const opts = shuffle([change, ...uniq], Math.random);
    const wrap = $('changeOpts');
    wrap.innerHTML = '';
    let wrong = 0;
    opts.forEach((v) => {
      const b = document.createElement('button');
      b.className = 'btn cyan';
      b.textContent = soles(v);
      b.addEventListener('click', () => {
        if (b.classList.contains('no') || wrap.dataset.done) return;
        if (v === change) {
          wrap.dataset.done = '1';
          b.classList.add('yes');
          this.audio.good();
          setTimeout(() => this.finish(paid, change), 650);
        } else {
          wrong++;
          this.mistakes++;
          b.classList.add('no');
          this.audio.soft();
          $('changeQ').innerHTML = `Casi. Piensa: ${soles(paid)} menos ${soles(this.opts.total)}…`;
          if (wrong >= 2) {
            wrap.dataset.done = '1';
            [...wrap.children].forEach((c) => c.textContent === soles(change) && c.classList.add('yes'));
            $('changeQ').innerHTML = `El vuelto es <b>${soles(change)}</b>. ¡La próxima te sale!`;
            setTimeout(() => this.finish(paid, change), 1600);
          }
        }
      });
      wrap.appendChild(b);
    });
    delete wrap.dataset.done;
    setTimeout(() => wrap.firstElementChild && wrap.firstElementChild.focus({ preventScroll: true }), 80);
  }

  finish(paid, change) {
    this.active = false;
    // la plata de la bandeja "se va" a la caja
    [...this.trayItems.children].forEach((el, i) => {
      el.style.transition = `transform .5s cubic-bezier(.5,-0.4,.7,1) ${i * 0.04}s, opacity .3s ${0.25 + i * 0.04}s`;
      el.style.transform = 'translate(0, -160px) scale(0.5)';
      el.style.opacity = '0';
    });
    this.audio.register();
    $('payAsk').textContent = change > 0 ? `¡Gracias! Tu vuelto: ${soles(change)}` : '¡Pagaste justo! ¡Gracias!';
    setTimeout(() => this.resolve({ paid, change, mistakes: this.mistakes }), 1100);
  }

  /** Atajo de pruebas: paga con estos valores (en céntimos) y responde el vuelto correcto. */
  debugPay(values, answerChange = true) {
    const pool = [...this.wallet.children];
    for (const v of values) {
      const el = pool.find((e) => +e.dataset.v === v && e.parentElement === this.wallet);
      if (el) this.move(el, this.trayItems);
      else {
        const extra = this.makeMoney(v);
        this.trayItems.appendChild(extra);
      }
    }
    this.refresh();
    this.pay();
    if (answerChange && this.answered && !$('changeBox').classList.contains('hidden')) {
      const change = this.sum() - this.opts.total;
      const b = [...$('changeOpts').children].find((c) => c.textContent === soles(change));
      b && b.click();
    }
  }
}
