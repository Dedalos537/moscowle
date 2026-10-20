import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { NotificationPresenterService } from '../../../core/notifications/notification-presenter.service';

/** Snackbar (PRP 011): algo pasó y hay una acción. Abajo; ancho completo en móvil. Se pausa con puntero o foco. */
@Component({
  selector: 'app-snackbar',
  imports: [FontAwesomeModule],
  templateUrl: './snackbar.html',
  styleUrl: './snackbar.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Snackbar {
  readonly presenter = inject(NotificationPresenterService);

  act() {
    const n = this.presenter.snackbar();
    if (n) this.presenter.open(n);
    this.presenter.dismissSnackbar();
  }
}
