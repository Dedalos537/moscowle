import { Component, input, output, ChangeDetectionStrategy, ChangeDetectorRef, effect, inject } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-input',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './input.html',
  styleUrl: './input.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Input {
  id = input<string>('');
  label = input<string>('');
  type = input<string>('text');
  placeholder = input<string>('');
  value = input<string | number>('');
  error = input<string>();
  icon = input<IconProp>();

  valueChange = output<string | number>();

  private cdr = inject(ChangeDetectorRef);

  constructor() {
    effect(() => {
      this.value();
      this.cdr.markForCheck();
    });
  }

  onInput(event: Event) {
    const input = event.target as HTMLInputElement;
    const val = input.type === 'number' ? parseFloat(input.value) || 0 : input.value;
    this.valueChange.emit(val);
  }
}
