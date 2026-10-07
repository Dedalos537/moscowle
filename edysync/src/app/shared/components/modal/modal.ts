import { Component, input, output, ChangeDetectionStrategy, ChangeDetectorRef, effect, inject } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { FocusTrap } from '../../directives/focus-trap';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [FontAwesomeModule, FocusTrap],
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Modal {
  isOpen = input(false);
  title = input<string>('');
  allowOverflow = input(false);
  /** Ancho del panel: sm 26rem · md 32rem (por defecto) · lg 44rem · xl 56rem. */
  size = input<'sm' | 'md' | 'lg' | 'xl'>('md');

  close = output<void>();

  /** Id estable del título: el panel lo referencia con aria-labelledby. */
  private static seq = 0;
  readonly titleId = `modal-title-${++Modal.seq}`;

  private cdr = inject(ChangeDetectorRef);

  constructor() {
    // Force re-render when isOpen changes (parent OnPush may not propagate to child signal input reliably)
    effect(() => {
      this.isOpen();
      this.cdr.markForCheck();
    });
  }

  closeModal() {
    this.close.emit();
  }
}
