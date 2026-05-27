import { Component, Input, Output, EventEmitter } from '@angular/core';
import { ConfirmState } from '../../../core/services/confirm.service';

@Component({
  selector: 'app-confirm-dialog',
  standalone: false,
  templateUrl: './confirm-dialog.html',
  styleUrl: './confirm-dialog.scss'
})
export class ConfirmDialog {
  @Input() state!: ConfirmState;
  @Output() confirm = new EventEmitter<void>();
  @Output() cancel = new EventEmitter<void>();
}
