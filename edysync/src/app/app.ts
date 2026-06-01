import { Component, OnInit, OnDestroy } from '@angular/core';
import { RecordingService } from './core/services/recording.service';
import { AuthService } from './core/services/auth.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.html',
  standalone: false,
  styleUrl: './app.scss'
})
export class App implements OnInit, OnDestroy {
  splashReady = false;

  constructor(
    private recordingService: RecordingService,
    private authService: AuthService,
  ) {}

  ngOnInit() {
    this.recordingService.iniciarPolleo();
    this.authService.currentUser$.subscribe(() => {
      setTimeout(() => { this.splashReady = true; }, 800);
    });
  }

  ngOnDestroy() {
    this.recordingService.detenerPolleo();
  }
}
