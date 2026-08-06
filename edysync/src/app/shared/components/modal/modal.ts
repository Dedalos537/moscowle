import { Component, input, output, ChangeDetectionStrategy, ChangeDetectorRef, effect, inject } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Modal {
  isOpen = input(false);
  title = input<string>('');
  allowOverflow = input(false);

  close = output<void>();

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
