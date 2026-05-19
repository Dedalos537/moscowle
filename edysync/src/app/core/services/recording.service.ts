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
  private currentSessionId: number | null = null;

  constructor(
    private http: HttpClient,
    private zone: NgZone,
  ) {}

  startPolling() {
    this.stopPolling();
    this.pollSubscription = interval(30000).subscribe(() => this.checkSessions());
    this.checkSessions();
  }

  stopPolling() {
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
    if (!user || user.role !== 'terapista') return;
    if (this.recordingState$.value === 'recording' || this.recordingState$.value === 'starting') return;

    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;
    const tomorrowStr = `${yyyy}-${mm}-${String(today.getDate() + 1).padStart(2, '0')}`;

    this.http.get<any[]>(`/api/sessions?start=${todayStr}&end=${tomorrowStr}`).subscribe({
      next: (sessions) => {
        if (!sessions || sessions.length === 0) return;
        const now = new Date();
        for (const s of sessions) {
          if (this.checkedSessions.has(s.id)) continue;
          if (s.status === 'completed' || s.status === 'cancelled' || s.status === 'in_progress') {
            this.checkedSessions.add(s.id);
            continue;
          }
          if (s.attendance === 'present' || s.attendance === 'absent') {
            this.checkedSessions.add(s.id);
            continue;
          }
          const start = new Date(s.start);
          const end = s.end ? new Date(s.end) : new Date(start.getTime() + 60 * 60 * 1000);
          const nowMs = now.getTime();
          const startMs = start.getTime();
          const endMs = end.getTime();

          if (nowMs >= startMs && nowMs <= endMs) {
            this.checkedSessions.add(s.id);
            this.currentSessionId = s.id;
            const patientName = s.patient?.name || s.extendedProps?.patient || '';
            this.sessionTitle$.next(s.title || 'Sesión');
            this.patientName$.next(patientName);
            this.activeSession$.next(s);
            this.autoStart();
            return;
          }

          if (nowMs > endMs + 5 * 60 * 1000 && s.status === 'scheduled') {
            this.checkedSessions.add(s.id);
            this.markNoShow(s.id);
          }
        }
      },
      error: (err) => console.warn('[RecordingService] Error fetching sessions:', err),
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
      }, 5 * 60 * 1000);
    });

    // Schedule attendance check 5 minutes after recording starts
    this.attendanceCheckTimer = setTimeout(() => {
      this.runAttendanceCheck();
    }, 5 * 60 * 1000);

    this.scheduleEnd();
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
      this.uploadChunk(blob);
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

  private uploadChunk(blob: Blob) {
    if (!this.currentSessionId) return;
    this.chunkStatus$.next(`Transcribiendo segmento ${this.chunkCount}...`);
    const fd = new FormData();
    fd.append('audio_file', blob, `session_${this.currentSessionId}_chunk${this.chunkCount}_${Date.now()}.webm`);
    this.http.post(`/api/sessions/${this.currentSessionId}/audio`, fd).subscribe({
      next: (data: any) => {
        if (data.success) {
          this.chunkStatus$.next(`Segmento ${this.chunkCount} transcrito`);
          this.http.post(`/api/sessions/${this.currentSessionId}/analyze-attendance`, {}).subscribe();
        }
      },
      error: () => this.chunkStatus$.next('Error al transcribir'),
    });
  }

  private scheduleEnd() {
    if (!this.currentSessionId) return;
    const session = this.activeSession$.value;
    if (!session) return;
    const endTime = session.end ? new Date(session.end).getTime() : new Date(session.start).getTime() + 60 * 60 * 1000;
    const timeLeft = endTime - Date.now();
    if (timeLeft > 0) {
      this.endTimer = setTimeout(() => {
        this.finishSession();
      }, timeLeft + 60 * 1000);
    }
  }

  private finishSession() {
    this.stopRecording();
    this.recordingState$.next('completed');
    if (!this.currentSessionId) {
      setTimeout(() => this.recordingState$.next('idle'), 3000);
      return;
    }

    const sessionId = this.currentSessionId;
    const sessionTitle = this.sessionTitle$.value;

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
    this.showAttendanceCheck$.next(false);
    this.auditScore$.next(null);
  }

  private reset() {
    this.stopRecording();
    this.activeSession$.next(null);
    this.recordingState$.next('idle');
    this.currentSessionId = null;
    this.checkedSessions.clear();
    this.showAttendanceCheck$.next(false);
    this.auditScore$.next(null);
  }
}
