import { Component, ChangeDetectionStrategy, inject } from '@angular/core';
import { SplashService } from '../../../core/services/splash.service';

/**
 * Entrada con «reveal mask» (como la de X): sobre el color de marca, el logo se encoge un instante y luego
 * crece hasta llenar la pantalla; la app aparece a través de su silueta. Con movimiento reducido, se desvanece.
 */
@Component({
  selector: 'app-splash-screen',
  standalone: true,
  templateUrl: './splash-screen.html',
  styleUrl: './splash-screen.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SplashScreen {
  private splash = inject(SplashService);
  readonly phase = this.splash.phase;
  /** URL absoluta: la app se sirve con base `/` (cPanel) o `/app/` (LAN). */
  readonly silhouette = `url("${new URL('assets/img/logo-silhouette.png', document.baseURI).href}")`;
  readonly logo = `url("${new URL('assets/img/logo.svg', document.baseURI).href}")`;

  onAnimationEnd(event: AnimationEvent) {
    if (event.target === event.currentTarget && event.animationName.includes('splash-out')) this.splash.finish();
  }
}
