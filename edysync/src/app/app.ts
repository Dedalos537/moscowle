import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { RecordingService } from './core/services/recording.service';
import { AuthService } from './core/services/auth.service';
import { FloatingUiService } from './core/services/floating-ui.service';
import { SplashScreen } from './shared/components/splash-screen/splash-screen';
import { AlertModal } from './shared/components/alert-modal/alert-modal.component';
import { ToastContainer } from './shared/components/toast-container/toast-container';
import { RecordingOverlay } from './shared/components/recording-overlay/recording-overlay';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, SplashScreen, AlertModal, ToastContainer, RecordingOverlay],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  splashReady = false;
  private sub = new Subscription();
  private floatingUi = inject(FloatingUiService);

  constructor(
    private recordingService: RecordingService,
    private authService: AuthService,
    private router: Router,
  ) {}

  ngOnInit() {
    this.floatingUi.attach();
    this.recordingService.iniciarPolleo();

    // Siempre ocultar splash aunque falle auth o la sesión quede colgada
    setTimeout(() => { this.splashReady = true; }, 1200);

    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.authService.verifySession().subscribe({
        next: (res) => {
          if (res?.role === 'terapista') {
            this.recordingService.onUserAuthenticated();
          }
        },
        error: () => {
          this.authService.clearSession();
          this.router.navigate(['/auth/login']);
        },
      });
    }
    this.sub.add(
      this.authService.currentUser$.subscribe(user => {
        if (user?.role === 'terapista') {
          this.recordingService.onUserAuthenticated();
        }
      })
    );
  }

  ngOnDestroy() {
    this.recordingService.detenerPolleo();
    this.sub.unsubscribe();
  }
}
