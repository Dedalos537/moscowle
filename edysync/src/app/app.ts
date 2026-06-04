import { Component, OnInit, OnDestroy } from '@angular/core';
import { RouterModule } from '@angular/router';
import { RecordingService } from './core/services/recording.service';
import { AuthService } from './core/services/auth.service';
import { SplashScreen } from './shared/components/splash-screen/splash-screen';
import { AlertModal } from './shared/components/alert-modal/alert-modal.component';
import { RecordingOverlay } from './shared/components/recording-overlay/recording-overlay';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterModule, SplashScreen, AlertModal, RecordingOverlay],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  splashReady = false;
  private sub = new Subscription();

  constructor(
    private recordingService: RecordingService,
    private authService: AuthService,
  ) {}

  ngOnInit() {
    this.recordingService.iniciarPolleo();
    this.sub.add(
      this.authService.currentUser$.subscribe(() => {
        setTimeout(() => { this.splashReady = true; }, 800);
      })
    );
  }

  ngOnDestroy() {
    this.recordingService.detenerPolleo();
    this.sub.unsubscribe();
  }
}
