import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'app-modal',
  standalone: false,
  templateUrl: './modal.html',
  styleUrl: './modal.scss'
})
export class Modal {
  @Input() isOpen: boolean = false;
  @Input() title: string = '';
  
  @Output() close = new EventEmitter<void>();

  closeModal() {
    this.close.emit();
  }
}
