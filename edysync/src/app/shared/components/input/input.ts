import { Component, Input as NgInput, Output, EventEmitter } from '@angular/core';
import { IconProp } from '@fortawesome/fontawesome-svg-core';

@Component({
  selector: 'app-input',
  standalone: false,
  templateUrl: './input.html',
  styleUrl: './input.scss'
})
export class Input {
  @NgInput() id: string = '';
  @NgInput() label: string = '';
  @NgInput() type: string = 'text';
  @NgInput() placeholder: string = '';
  @NgInput() value: string | number = '';
  @NgInput() error?: string;
  @NgInput() icon?: IconProp;

  @Output() valueChange = new EventEmitter<string | number>();

  onInput(event: Event) {
    const input = event.target as HTMLInputElement;
    const val = input.type === 'number' ? parseFloat(input.value) || 0 : input.value;
    this.value = val;
    this.valueChange.emit(val);
  }
}
