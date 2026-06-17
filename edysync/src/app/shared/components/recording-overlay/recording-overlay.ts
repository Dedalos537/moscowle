import { Component, OnInit, OnDestroy, ChangeDetectionStrategy } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router } from '@angular/router';
import { RecordingService } from '../../../core/services/recording.service';
import { Observable } from 'rxjs';
import { Button } from '../button/button';

@Component({
  selector: 'app-recording-overlay',
  standalone: true,
  imports: [AsyncPipe, FontAwesomeModule, Button],
  templateUrl: './recording-overlay.html',
  styleUrl: './recording-overlay.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RecordingOverlay implements OnInit, OnDestroy {
  state: Observable<'idle' | 'starting' | 'recording' | 'mic_error' | 'completed'>;
  elapsed: Observable<string>;
  chunkStatus: Observable<string>;
  sessionTitle: Observable<string>;
  patientName: Observable<string>;
  showAttendanceCheck: Observable<boolean>;
  attendanceCountdown: Observable<number>;
  auditScore: Observable<number | null>;
  sessionGateActive: Observable<boolean>;
  sessionGateMode: Observable<'late' | 'recording' | null>;
  delayMinutes: Observable<number>;

  constructor(
    private recordingService: RecordingService,
    private router: Router,
  ) {
    this.state = this.recordingService.recordingState$;
    this.elapsed = this.recordingService.elapsedTime$;
    this.chunkStatus = this.recordingService.chunkStatus$;
    this.sessionTitle = this.recordingService.sessionTitle$;
    this.patientName = this.recordingService.patientName$;
    this.showAttendanceCheck = this.recordingService.showAttendanceCheck$;
    this.attendanceCountdown = this.recordingService.attendanceCountdown$;
    this.auditScore = this.recordingService.auditScore$;
    this.sessionGateActive = this.recordingService.sessionGateActive$;
    this.sessionGateMode = this.recordingService.sessionGateMode$;
    this.delayMinutes = this.recordingService.delayMinutes$;
  }

  ngOnInit() {}

  ngOnDestroy() {}

  goToSession() {
    const id = this.recordingService.activeSession$.value?.id;
    if (id) {
      this.router.navigate(['/therapist/session-review', id]);
    }
  }

  retryMic() {
    this.recordingService.retryMic();
  }

  markPresent() {
    this.recordingService.markPatientPresent();
  }

  markAbsent() {
    this.recordingService.markPatientAbsent();
  }

  startLateSession() {
    this.recordingService.confirmLateSessionStart();
  }

  getLateDelayLabel(): string {
    return this.recordingService.getLateDelayLabel();
  }
}
