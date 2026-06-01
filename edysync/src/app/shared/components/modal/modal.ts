import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';

@Component({
  selector: 'app-modal',
  standalone: false,
  templateUrl: './modal.html',
  styleUrl: './modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Modal {
  @Input() isOpen: boolean = false;
  @Input() title: string = '';

  @Output() close = new EventEmitter<void>();

  constructor(private cdr: ChangeDetectorRef) {}

  closeModal() {
    this.close.emit();
  }
}
