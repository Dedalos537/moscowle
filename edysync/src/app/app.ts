import { Component, OnInit, OnDestroy, inject, ChangeDetectorRef } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { RecordingService } from './core/services/recording.service';
import { AuthService } from './core/services/auth.service';
import { FloatingUiService } from './core/services/floating-ui.service';
import { PreloadService } from './core/services/preload.service';
import { SplashScreen } from './shared/components/splash-screen/splash-screen';
import { AlertModal } from './shared/components/alert-modal/alert-modal.component';
import { ToastContainer } from './shared/components/toast-container/toast-container';
import { RecordingOverlay } from './shared/components/recording-overlay/recording-overlay';
import { ServerDownGame } from './shared/components/server-down-game/server-down-game';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { environment } from '../environments/environment';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, FontAwesomeModule, SplashScreen, AlertModal, ToastContainer, RecordingOverlay, ServerDownGame],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  splashReady = false;
  serverDown = false;
  retrying = false;
  private sub = new Subscription();
  private floatingUi = inject(FloatingUiService);

  constructor(
    private recordingService: RecordingService,
    private authService: AuthService,
    private preload: PreloadService,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.floatingUi.attach();
    this.recordingService.iniciarPolleo();

    this.checkBackend().then(up => {
      this.serverDown = !up;
      this.splashReady = true;
      this.cdr.markForCheck();

      if (up) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          this.authService.verifySession().subscribe({
            next: (res) => {
              if (res?.role === 'terapista') {
                this.recordingService.onUserAuthenticated();
              }
            },
            error: () => {},
          });
        }
        this.sub.add(
          this.authService.currentUser$.subscribe(user => {
            this.preload.preloadFor(user?.role);
            if (user?.role === 'terapista') {
              this.recordingService.onUserAuthenticated();
            }
          })
        );
      }
    });
  }

  private async checkBackend(): Promise<boolean> {
    const base = environment.apiBaseUrl || '';
    try {
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 15000);
      const res = await fetch(`${base}/api/public/app-key`, {
        method: 'HEAD',
        signal: ctrl.signal,
        cache: 'no-store',
      });
      clearTimeout(timer);
      return res.ok;
    } catch {
      return false;
    }
  }

  retryPage() {
    this.retrying = true;
    this.cdr.markForCheck();
    this.checkBackend().then(up => {
      if (up) {
        window.location.reload();
      } else {
        this.retrying = false;
        this.cdr.markForCheck();
      }
    });
  }

  ngOnDestroy() {
    this.recordingService.detenerPolleo();
    this.sub.unsubscribe();
  }
}
