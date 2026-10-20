import { ChangeDetectionStrategy, Component, ElementRef, effect, inject, viewChild } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { NotificationPresenterService } from '../../../core/notifications/notification-presenter.service';

/**
 * Modal de notificación (PRP 011): exige acuse («Entendido»). Diálogo centrado en PC y hoja inferior en móvil.
 * Uno a la vez (cola). El foco entra al abrir y vuelve a donde estaba al cerrar.
 */
@Component({
  selector: 'app-notification-sheet',
  imports: [FontAwesomeModule],
  templateUrl: './notification-sheet.html',
  styleUrl: './notification-sheet.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationSheet {
  readonly presenter = inject(NotificationPresenterService);
  private readonly ok = viewChild<ElementRef<HTMLButtonElement>>('okBtn');
  private returnTo: HTMLElement | null = null;

  constructor() {
    effect(() => {
      const open = this.presenter.modals().length > 0;
      const btn = this.ok();
      if (open && btn) {
        this.returnTo ??= document.activeElement as HTMLElement | null;
        queueMicrotask(() => btn.nativeElement.focus());
      }
    });
  }

  acknowledge(openAction = false) {
    const n = this.presenter.modals()[0];
    if (openAction && n) this.presenter.open(n);
    this.presenter.acknowledgeModal();
    if (!this.presenter.modals().length) {
      this.returnTo?.focus?.();
      this.returnTo = null;
    }
  }
}
