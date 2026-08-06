import { Component, input, output, ChangeDetectionStrategy, ChangeDetectorRef, effect, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-button',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule],
  templateUrl: './button.html',
  styleUrl: './button.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Button {
  label = input<string>('');
  variant = input<'primary' | 'secondary' | 'danger' | 'ghost'>('primary');
  icon = input<IconProp>();
  disabled = input(false);
  loading = input(false);
  type = input<'button' | 'submit'>('button');

  clicked = output<Event>();

  private cdr = inject(ChangeDetectorRef);

  readonly variantMap: Record<string, Record<string, boolean>> = {
    primary: { 'btn--primary': true },
    secondary: { 'btn--secondary': true },
    danger: { 'btn--danger': true },
    ghost: { 'btn--ghost': true }
  };

  constructor() {
    effect(() => {
      // Track all signal inputs so changes trigger CD in OnPush
      this.variant();
      this.disabled();
      this.loading();
      this.cdr.markForCheck();
    });
  }

  get btnClass(): Record<string, boolean> {
    return {
      ...this.variantMap[this.variant()],
      'btn--disabled': this.disabled()
    };
  }

  onClick(event: Event) {
    if (!this.disabled()) {
      this.clicked.emit(event);
    }
  }
}
