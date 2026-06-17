import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Subscription } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class RecordingService {
  activeSession$ = new BehaviorSubject<any>(null);
  isRecording$ = new BehaviorSubject<boolean>(false);
  recordingState$ = new BehaviorSubject<'idle' | 'starting' | 'recording' | 'mic_error' | 'completed'>('idle');
  elapsedTime$ = new BehaviorSubject<string>('00:00');
  chunkStatus$ = new BehaviorSubject<string>('');
  canLogout$ = new BehaviorSubject<boolean>(true);
  sessionTitle$ = new BehaviorSubject<string>('Sesión');
  patientName$ = new BehaviorSubject<string>('');
  showAttendanceCheck$ = new BehaviorSubject<boolean>(false);
  attendanceCountdown$ = new BehaviorSubject<number>(120);
  auditScore$ = new BehaviorSubject<number | null>(null);
  pendingLateSession$ = new BehaviorSubject<any>(null);

  private pollSubscription?: Subscription;
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private chunkTimer: any;
  private elapsedTimer: any;
  private endTimer: any;
  private attendanceCheckTimer: any;
  private attendanceCountdownInterval: any;
  private recordingStartTime: number = 0;
  private chunkCount: number = 0;
  private audioChunks: Blob[] = [];
  private checkedSessions: Set<number> = new Set();
  private dismissedSessions: Set<number> = new Set();
  private readonly chunkIntervalMs = 5 * 60 * 1000;
  private currentSessionId: number | null = null;
  private pendingUploads = 0;
  private finishPending = false;
  private finishSessionId: number | null = null;
  private finishSessionTitle = '';

  constructor(
    private http: HttpClient,
    private zone: NgZone,
  ) {}

  iniciarPolleo() {
    this.detenerPolleo();
    this.pollSubscription = interval(10000).subscribe(() => this.checkSessions());
    this.checkSessions();
  }

  onUserAuthenticated() {
    this.checkedSessions.clear();
    this.dismissedSessions.clear();
    this.checkSessions();
  }

  dismissLateSession(sessionId?: number) {
    const id = sessionId || this.currentSessionId || this.pendingLateSession$.value?.id;
    if (id) this.dismissedSessions.add(id);
    this.pendingLateSession$.next(null);
  }

  detenerPolleo() {
    this.pollSubscription?.unsubscribe();
  }

  private getCurrentUser(): any {
    try {
      const stored = localStorage.getItem('user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  private checkSessions() {
    const user = this.getCurrentUser();
    if (!user || user.role !== 'terapista') {
      this.activeSession$.next(null);
      return;
    }
    if (this.recordingState$.value === 'recording' || this.recordingState$.value === 'starting') return;

    this.http.post('/api/sessions/auto-complete-expired', {}).subscribe({
      error: () => {},
    });

    this.http.get<any>('/api/sessions/current').subscribe({
      next: (res) => {
        if (!res.success || !res.has_active) return;
        const s = res.session;
        if (this.dismissedSessions.has(s.id)) return;
        if (this.checkedSessions.has(s.id)) return;

        const delayMinutes = res.delay_minutes ?? 0;

        if (s.status === 'scheduled' && delayMinutes >= 0 && delayMinutes <= 10) {
          this.currentSessionId = s.id;
          const patientName = s.patient?.name || '';
          this.sessionTitle$.next(s.title || 'Sesión');
          this.patientName$.next(patientName);
          this.activeSession$.next(s);
          this.pendingLateSession$.next(s);
          return;
        }

        this.currentSessionId = s.id;
        const patientName = s.patient?.name || '';
        this.sessionTitle$.next(s.title || 'Sesión');
        this.patientName$.next(patientName);
        this.activeSession$.next(s);
        this.checkedSessions.add(s.id);
        this.autoStart();
      },
      error: (err) => console.warn('[RecordingService] Error fetching current session:', err),
    });
  }

  startRecording(session: any) {
    this.currentSessionId = session.id;
    this.checkedSessions.add(session.id);
    const patientName = session.patient?.name || '';
    this.sessionTitle$.next(session.title || 'Sesión');
    this.patientName$.next(patientName);
    this.activeSession$.next(session);

    this.recordingState$.next('starting');
    this.isRecording$.next(true);
    this.canLogout$.next(false);

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      this._startRecording(stream);
    }).catch(() => {
      this.recordingState$.next('mic_error');
      this.isRecording$.next(false);
      this.canLogout$.next(true);
    });
  }

  private autoStart() {
    this.recordingState$.next('starting');
    this.isRecording$.next(true);
    this.canLogout$.next(false);

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      this._startRecording(stream);
    }).catch(() => {
      this.recordingState$.next('mic_error');
      this.isRecording$.next(false);
      this.canLogout$.next(true);
    });
  }

  retryMic() {
    this.recordingState$.next('starting');
    this.isRecording$.next(true);
    this.canLogout$.next(false);

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      this._startRecording(stream);
    }).catch(() => {
      this.recordingState$.next('mic_error');
      this.isRecording$.next(false);
      this.canLogout$.next(true);
    });
  }

  private _startRecording(stream: MediaStream) {
    this.stream = stream;
    this.recordingState$.next('recording');
    this.recordingStartTime = Date.now();
    this.chunkCount = 0;
    this.startNewChunk();

    if (this.currentSessionId) {
      this.http.post(`/api/sessions/${this.currentSessionId}/start-recording`, {}).subscribe();
    }

    this.zone.runOutsideAngular(() => {
      this.elapsedTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
        const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        this.zone.run(() => this.elapsedTime$.next(`${m}:${s}`));
      }, 1000);

      this.chunkTimer = setInterval(() => {
        if (this.recorder && this.recorder.state === 'recording') {
          this.recorder.stop();
        }
      }, this.chunkIntervalMs);
    });

    this.attendanceCheckTimer = setTimeout(() => {
      this.runAttendanceCheck();
    }, 5 * 60 * 1000);

    this.programarFin();
  }

  private runAttendanceCheck() {
    if (!this.currentSessionId) return;
    if (this.showAttendanceCheck$.value) return;
    this.http.post(`/api/sessions/${this.currentSessionId}/analyze-attendance`, {}).subscribe({
      next: (res: any) => {
        const coverage = res.coverage_pct || 0;
        const suggested = res.suggested_attendance;
        if (coverage < 5 || suggested === 'absent') {
          this.showAttendanceCheck$.next(true);
          this.attendanceCountdown$.next(120);
          this.zone.runOutsideAngular(() => {
            this.attendanceCountdownInterval = setInterval(() => {
              const current = this.attendanceCountdown$.value;
              if (current <= 1) {
                clearInterval(this.attendanceCountdownInterval);
                this.zone.run(() => this.markPatientAbsent());
              } else {
                this.zone.run(() => this.attendanceCountdown$.next(current - 1));
              }
            }, 1000);
          });
        }
      },
      error: () => {},
    });
  }

  markPatientPresent() {
    this.showAttendanceCheck$.next(false);
    clearInterval(this.attendanceCountdownInterval);
  }

  markPatientAbsent() {
    this.showAttendanceCheck$.next(false);
    clearInterval(this.attendanceCountdownInterval);
    this.stopRecording();
    this.markNoShow(this.currentSessionId!);
  }

  private startNewChunk() {
    this.audioChunks = [];
    const mimeType = this.getSupportedMimeType();
    try {
      this.recorder = new MediaRecorder(this.stream!, { mimeType });
    } catch {
      this.recorder = new MediaRecorder(this.stream!);
    }
    this.recorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    };
    this.recorder.onstop = () => {
      this.chunkCount++;
      const blob = new Blob(this.audioChunks, { type: this.recorder?.mimeType || 'audio/webm' });
      this.subirChunk(blob);
      if (this.isRecording$.value && this.stream?.active) {
        this.startNewChunk();
      }
    };
    this.recorder.start(1000);
  }

  private getSupportedMimeType(): string {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus'];
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
  }

  private subirChunk(blob: Blob, retriesRemaining = 3) {
    if (!this.currentSessionId) return;
    this.pendingUploads++;
    this.chunkStatus$.next(`Transcribiendo bloque ${this.chunkCount}...`);
    const fd = new FormData();
    fd.append('audio_file', blob, `session_${this.currentSessionId}_chunk${this.chunkCount}_${Date.now()}.webm`);
    this.http.post(`/api/sessions/${this.currentSessionId}/audio`, fd).subscribe({
      next: (data: any) => {
        this.pendingUploads--;
        if (data.success) {
          this.chunkStatus$.next(`Bloque ${this.chunkCount} transcrito`);
          this.http.post(`/api/sessions/${this.currentSessionId}/analyze-attendance`, {}).subscribe();
          this.http.get(`/api/sessions/${this.currentSessionId}/compare-live`).subscribe({
            next: (cmp: any) => {
              if (cmp.success && cmp.score_vectorial != null) {
                this.auditScore$.next(cmp.score_vectorial);
              }
            }
          });
        }
        this.tryFinishAfterUpload();
      },
      error: () => {
        this.pendingUploads--;
        if (retriesRemaining > 1) {
          this.chunkStatus$.next(`Reintentando bloque ${this.chunkCount}...`);
          setTimeout(() => this.subirChunk(blob, retriesRemaining - 1), 2000);
        } else {
          this.chunkStatus$.next('Error al transcribir');
          this.tryFinishAfterUpload();
        }
      },
    });
  }

  private programarFin() {
    if (!this.currentSessionId) return;
    const session = this.activeSession$.value;
    if (!session) return;
    const endTime = session.end
      ? new Date(session.end).getTime()
      : new Date(session.start).getTime() + 60 * 60 * 1000;
    const timeLeft = endTime - Date.now();
    if (timeLeft > 0) {
      this.endTimer = setTimeout(() => {
        this.finishSession();
      }, timeLeft + 60 * 1000);
    }
  }

  private tryFinishAfterUpload() {
    if (this.finishPending && this.pendingUploads === 0) {
      this.finishPending = false;
      this.doFinishSession(this.finishSessionId!, this.finishSessionTitle);
    }
  }

  private finishSession() {
    this.finishPending = true;
    this.finishSessionId = this.currentSessionId;
    this.finishSessionTitle = this.sessionTitle$.value;
    this.stopRecording();
    this.recordingState$.next('completed');

    if (!this.finishSessionId) {
      setTimeout(() => this.recordingState$.next('idle'), 3000);
      this.finishPending = false;
      return;
    }

    if (this.pendingUploads === 0) {
      this.finishPending = false;
      this.doFinishSession(this.finishSessionId, this.finishSessionTitle);
    }
  }

  private doFinishSession(sessionId: number, sessionTitle: string) {
    this.http.post(`/api/sessions/${sessionId}/complete`, {}).subscribe({
      next: () => {
        this.http.post(`/api/sessions/${sessionId}/audit`, {}).subscribe({
          next: (auditRes: any) => {
            if (auditRes.success) {
              const score = auditRes.report?.audit_score ?? auditRes.report?.score ?? null;
              if (score !== null) this.auditScore$.next(score);
              const msg = score !== null
                ? `Auditoria completada para "${sessionTitle}" — Puntuacion: ${score}/100`
                : `Auditoria completada para "${sessionTitle}"`;
              this.http.post(`/api/notifications/create`, { message: msg }).subscribe();
            }
          },
          error: () => {
            this.http.post(`/api/notifications/create`, {
              message: `Auditoria disponible para "${sessionTitle}" (revisar manualmente)`,
            }).subscribe();
          },
        });
        setTimeout(() => this.reset(), 4000);
      },
      error: () => {
        setTimeout(() => this.reset(), 4000);
      },
    });
  }

  markNoShow(sessionId?: number) {
    const id = sessionId || this.currentSessionId;
    if (!id) return;
    this.http.post(`/api/sessions/${id}/mark-absent`, {}).subscribe({
      next: () => this.reset(),
      error: () => this.reset(),
    });
  }

  stopRecording() {
    this.isRecording$.next(false);
    this.canLogout$.next(true);
    clearInterval(this.chunkTimer);
    clearInterval(this.elapsedTimer);
    clearTimeout(this.endTimer);
    clearTimeout(this.attendanceCheckTimer);
    clearInterval(this.attendanceCountdownInterval);
    if (this.recorder && this.recorder.state === 'recording') {
      this.recorder.stop();
    }
    if (this.stream) {
      this.stream.getTracks().forEach(t => t.stop());
      this.stream = null;
    }
    this.recorder = null;
  }

  forceStopAndLogout() {
    this.stopRecording();
    this.recordingState$.next('idle');
    this.currentSessionId = null;
    this.activeSession$.next(null);
    this.checkedSessions.clear();
    this.dismissedSessions.clear();
    this.showAttendanceCheck$.next(false);
    this.auditScore$.next(null);
  }

  private reset() {
    this.stopRecording();
    this.activeSession$.next(null);
    this.recordingState$.next('idle');
    this.currentSessionId = null;
    this.checkedSessions.clear();
    this.dismissedSessions.clear();
    this.showAttendanceCheck$.next(false);
    this.auditScore$.next(null);
  }
}
