// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit, OnDestroy } from '@angular/core';
import { Router } from '@angular/router';
import { RecordingService } from '../../../core/services/recording.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-recording-overlay',
  standalone: false,
  templateUrl: './recording-overlay.html',
  styleUrl: './recording-overlay.scss',
})
export class RecordingOverlay implements OnInit, OnDestroy {
  // DCE — Diego Centeno Estuvo Acá
  state: Observable<'idle' | 'starting' | 'recording' | 'mic_error' | 'completed'>;
  elapsed: Observable<string>;
  chunkStatus: Observable<string>;
  sessionTitle: Observable<string>;
  patientName: Observable<string>;
  showAttendanceCheck: Observable<boolean>;
  attendanceCountdown: Observable<number>;
  auditScore: Observable<number | null>;

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
}
