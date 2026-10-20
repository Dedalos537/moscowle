import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Notice, NotificationPresenterService } from '../../../core/notifications/notification-presenter.service';

/** Banners (PRP 011): estados que siguen vigentes (servidor caído, MiMo en pausa, cuotas vencidas). Bajo la cabecera. */
@Component({
  selector: 'app-notice-banners',
  imports: [FontAwesomeModule],
  templateUrl: './notice-banners.html',
  styleUrl: './notice-banners.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NoticeBanners {
  readonly presenter = inject(NotificationPresenterService);
  readonly expanded = signal(false);
  /** Con 2 o más, en móvil se pliegan en «N avisos»; en PC se ven hasta 2 y el resto al expandir. */
  readonly visible = computed(() => {
    const list = this.presenter.banners();
    return this.expanded() ? list : list.slice(0, 2);
  });
  readonly hidden = computed(() => this.presenter.banners().length - this.visible().length);

  act(n: Notice) {
    this.presenter.open(n);
  }
}
