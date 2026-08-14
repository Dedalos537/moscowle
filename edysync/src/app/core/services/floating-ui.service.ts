import { Injectable, signal, DestroyRef, inject } from '@angular/core';

const FLOATING_SELECTOR =
  '.floating-ui, app-ai-chat, app-help-button, app-charts-toggle, app-toast-container, .route-loader, .recording-overlay';

const OVERLAY_SELECTORS = [
  '.modal-overlay',
  '.confirm-backdrop',
  '.help-backdrop',
  '.help-overlay',
  '.sidebar-overlay',
  '.beacon-backdrop.is-visible',
];

const TEXT_TAGS = new Set([
  'P', 'SPAN', 'TD', 'TH', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6',
  'LABEL', 'STRONG', 'EM', 'A', 'BUTTON', 'DT', 'DD',
]);

@Injectable({ providedIn: 'root' })
export class FloatingUiService {
  readonly hidden = signal(false);
  readonly leftBaseBottom = signal(24);
  readonly rightBaseBottom = signal(24);
  readonly rightInset = signal(24);

  private destroyRef = inject(DestroyRef);
  private attached = false;
  private observer: MutationObserver | null = null;
  private repositionTimer: ReturnType<typeof setTimeout> | null = null;

  attach(): void {
    if (this.attached || typeof document === 'undefined') return;
    this.attached = true;

    const schedule = () => {
      if (this.repositionTimer) clearTimeout(this.repositionTimer);
      this.repositionTimer = setTimeout(() => this.reposition(), 120);
    };

    this.observer = new MutationObserver(() => {
      this.updateOverlayHidden();
      schedule();
    });
    this.observer.observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style', 'open'] });

    window.addEventListener('scroll', schedule, { passive: true, capture: true });
    window.addEventListener('resize', schedule, { passive: true });

    this.destroyRef.onDestroy(() => this.detach());

    this.updateOverlayHidden();
    this.reposition();
  }

  detach(): void {
    this.attached = false;
    this.observer?.disconnect();
    this.observer = null;
    if (this.repositionTimer) clearTimeout(this.repositionTimer);
  }

  leftStackOffset(slot: 0 | 1): number {
    const base = this.leftBaseBottom();
    return slot === 0 ? base : base + 64;
  }

  private updateOverlayHidden(): void {
    // Overlays owned by the chat (its own confirm modal, rendered as a child of
    // <app-ai-chat>) must NOT hide the floating UI, otherwise the chat closes
    // itself the moment its confirmation dialog opens.
    const blocked = OVERLAY_SELECTORS.some((sel) =>
      Array.from(document.querySelectorAll(sel)).some((el) => !el.closest('app-ai-chat')),
    );
    if (this.hidden() !== blocked) {
      this.hidden.set(blocked);
    }
  }

  private reposition(): void {
    this.updateOverlayHidden();
    if (this.hidden()) return;

    const leftStackH = 120;
    const leftW = 200;
    const rightSize = 52;
    const margin = 16;

    const leftCandidates = [24, 72, 120, 168, 216];
    for (const bottom of leftCandidates) {
      const top = window.innerHeight - bottom - leftStackH - margin;
      if (!this.rectObstructed(margin, top, leftW, leftStackH)) {
        this.leftBaseBottom.set(bottom);
        break;
      }
    }

    const rightCandidates = [24, 72, 120, 168];
    const rightInsets = [24, 88, 152];
    let placed = false;
    for (const bottom of rightCandidates) {
      for (const inset of rightInsets) {
        const left = window.innerWidth - inset - rightSize - margin;
        const top = window.innerHeight - bottom - rightSize - margin;
        if (!this.rectObstructed(left, top, rightSize + 8, rightSize + 8)) {
          this.rightBaseBottom.set(bottom);
          this.rightInset.set(inset);
          placed = true;
          break;
        }
      }
      if (placed) break;
    }
  }

  private rectObstructed(left: number, top: number, width: number, height: number): boolean {
    const points: [number, number][] = [
      [left + width * 0.5, top + height * 0.5],
      [left + 10, top + height - 10],
      [left + width - 10, top + 10],
    ];

    for (const [x, y] of points) {
      if (x < 0 || y < 0 || x > window.innerWidth || y > window.innerHeight) continue;
      const stack = document.elementsFromPoint(x, y);
      for (const el of stack) {
        if (this.isBlockingContent(el)) return true;
      }
    }
    return false;
  }

  private isBlockingContent(el: Element): boolean {
    if (!(el instanceof HTMLElement)) return false;
    if (el.closest(FLOATING_SELECTOR)) return false;
    if (el.closest('nav, aside, header, .sidebar, .layout__sidebar, .layout__header')) return false;

    const inMain = el.closest(
      'main, .layout__content, .dashboard, article, table, [role="main"], [class*="content"]',
    );
    if (!inMain) return false;

    if (TEXT_TAGS.has(el.tagName)) {
      const text = el.innerText?.trim() ?? '';
      return text.length > 1;
    }

    const text = el.innerText?.trim() ?? '';
    return text.length > 8 && el.children.length <= 6;
  }
}
