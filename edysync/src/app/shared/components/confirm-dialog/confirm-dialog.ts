import { Component, input, output, ChangeDetectionStrategy } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ConfirmState } from '../../../core/services/confirm.service';
import { Button } from '../button/button';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [FontAwesomeModule, Button],
  templateUrl: './confirm-dialog.html',
  styleUrl: './confirm-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ConfirmDialog {
  state = input.required<ConfirmState>();
  confirm = output<void>();
  cancel = output<void>();

}
