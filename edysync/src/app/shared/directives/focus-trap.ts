import { AfterViewInit, Directive, ElementRef, HostListener, OnDestroy, inject } from '@angular/core';

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Patrón de diálogo accesible: al abrirse enfoca el panel, mantiene Tab/Shift+Tab dentro de él
 * y al destruirse devuelve el foco al elemento que lo abrió (WCAG 2.4.3 y 2.1.2).
 */
@Directive({
  selector: '[appFocusTrap]',
  standalone: true,
})
export class FocusTrap implements AfterViewInit, OnDestroy {
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  private previouslyFocused: HTMLElement | null = null;

  ngAfterViewInit(): void {
    this.previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    // El panel (tabindex -1) recibe el foco: el lector de pantalla anuncia el diálogo antes del primer control.
    queueMicrotask(() => this.host.nativeElement.focus({ preventScroll: true }));
  }

  ngOnDestroy(): void {
    this.previouslyFocused?.focus?.({ preventScroll: true });
  }

  @HostListener('keydown', ['$event'])
  onKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Tab') return;
    const items = this.focusable();
    if (items.length === 0) {
      event.preventDefault();
      return;
    }
    const first = items[0];
    const last = items[items.length - 1];
    const active = document.activeElement;
    const host = this.host.nativeElement;
    if (event.shiftKey && (active === first || active === host)) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  }

  private focusable(): HTMLElement[] {
    return Array.from(this.host.nativeElement.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      (el) => el.offsetParent !== null || el === document.activeElement,
    );
  }
}
