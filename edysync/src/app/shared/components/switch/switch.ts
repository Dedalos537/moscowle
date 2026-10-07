import { Component, ChangeDetectionStrategy, input, output } from '@angular/core';

/** Interruptor accesible (role="switch"): se mueve con teclado y comunica su estado a lectores de pantalla. */
@Component({
  selector: 'app-switch',
  standalone: true,
  imports: [],
  templateUrl: './switch.html',
  styleUrl: './switch.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Switch {
  checked = input(false);
  disabled = input(false);
  /** Nombre accesible; si el interruptor tiene una etiqueta visible usa `labelledby`. */
  label = input('');
  labelledby = input<string | null>(null);

  changed = output<boolean>();

  toggle() {
    if (!this.disabled()) this.changed.emit(!this.checked());
  }
}
