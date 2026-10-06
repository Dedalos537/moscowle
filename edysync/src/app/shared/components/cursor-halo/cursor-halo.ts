import { Component, ChangeDetectionStrategy, ElementRef, NgZone, OnDestroy, OnInit, ViewChild, effect, inject } from '@angular/core';
import { GlobalSettingsService } from '../../../core/services/global-settings.service';

/**
 * Halo que acompaña al puntero para saber dónde está. Solo en dispositivos con puntero fino (ratón/trackpad).
 * Rendimiento: un único elemento movido con `transform` en requestAnimationFrame, fuera de la zona de Angular
 * (no dispara detección de cambios) y con listeners pasivos.
 */
@Component({
  selector: 'app-cursor-halo',
  standalone: true,
  imports: [],
  templateUrl: './cursor-halo.html',
  styleUrl: './cursor-halo.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class CursorHalo implements OnInit, OnDestroy {
  @ViewChild('halo', { static: true }) halo!: ElementRef<HTMLElement>;

  private zone = inject(NgZone);
  private settings = inject(GlobalSettingsService);
  private x = 0;
  private y = 0;
  private raf = 0;
  private attached = false;
  private fine = typeof window !== 'undefined' && !!window.matchMedia?.('(pointer: fine)').matches;

  private static readonly INTERACTIVE = 'a[href], button, [role="button"], [role="tab"], [role="menuitem"], input, select, textarea, label, summary, [cdkDrag], .cdk-drag';

  constructor() {
    effect(() => {
      const on = this.settings.cursorHalo();
      if (on && this.fine) this.attach();
      else this.detach();
    });
  }

  ngOnInit() {
    this.halo.nativeElement.dataset['visible'] = 'false';
  }

  ngOnDestroy() {
    this.detach();
  }

  private move = (e: PointerEvent) => {
    if (e.pointerType === 'touch') return;
    this.x = e.clientX;
    this.y = e.clientY;
    if (!this.raf) this.raf = requestAnimationFrame(this.paint);
  };

  private paint = () => {
    this.raf = 0;
    const el = this.halo.nativeElement;
    el.style.transform = `translate3d(${this.x}px, ${this.y}px, 0)`;
    el.dataset['visible'] = 'true';
  };

  private over = (e: PointerEvent) => {
    const target = e.target as Element | null;
    this.halo.nativeElement.dataset['hover'] = target?.closest?.(CursorHalo.INTERACTIVE) ? 'true' : 'false';
  };

  private down = () => (this.halo.nativeElement.dataset['pressed'] = 'true');
  private up = () => (this.halo.nativeElement.dataset['pressed'] = 'false');
  private leave = () => (this.halo.nativeElement.dataset['visible'] = 'false');

  private attach() {
    if (this.attached) return;
    this.attached = true;
    this.zone.runOutsideAngular(() => {
      const opts: AddEventListenerOptions = { passive: true };
      document.addEventListener('pointermove', this.move, opts);
      document.addEventListener('pointerover', this.over, opts);
      document.addEventListener('pointerdown', this.down, opts);
      document.addEventListener('pointerup', this.up, opts);
      document.documentElement.addEventListener('pointerleave', this.leave, opts);
    });
  }

  private detach() {
    if (!this.attached) return;
    this.attached = false;
    document.removeEventListener('pointermove', this.move);
    document.removeEventListener('pointerover', this.over);
    document.removeEventListener('pointerdown', this.down);
    document.removeEventListener('pointerup', this.up);
    document.documentElement.removeEventListener('pointerleave', this.leave);
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
    this.halo.nativeElement.dataset['visible'] = 'false';
  }
}
