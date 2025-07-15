import { CommonModule } from '@angular/common';
import {
  Component,
  EventEmitter,
  Input,
  OnChanges,
  Output,
  SimpleChanges,
} from '@angular/core';

@Component({
  selector: 'app-service-card',
  imports: [CommonModule],
  templateUrl: './service-card.html',
  styleUrl: './service-card.css',
})
export class ServiceCard implements OnChanges {
  @Input() service!: any;
  @Input() category!: string;
  @Output() openModal = new EventEmitter<void>();

  colors = { primary: '#000', secondary: '#333' };
  hover = false;

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['category']) {
      this.colors = this.getCategoryColor(this.category);
    }
  }

  getCategoryColor(category: string) {
    const colorsMap: { [key: string]: { primary: string; secondary: string } } =
      {
        'Terapias Integrales': { primary: '#28a745', secondary: '#20c997' },
        Terapias: { primary: '#667eea', secondary: '#764ba2' },
        'Apoyo Virtual': { primary: '#17a2b8', secondary: '#6f42c1' },
        'Material Concreto': { primary: '#ffc107', secondary: '#fd7e14' },
      };
    return colorsMap[category] || { primary: '#000', secondary: '#333' };
  }

  verDetalle() {
    this.openModal.emit();
  }

  hideImage(event: any) {
    event.target.style.display = 'none';
  }
}
