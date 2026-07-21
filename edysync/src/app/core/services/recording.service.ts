import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, interval, Subscription } from 'rxjs';

export type SessionGateMode = 'late' | 'recording' | null;

@Injectable({ providedIn: 'root' })
export class RecordingService {
  activeSession$ = new BehaviorSubject<any>(null);
  isRecording$ = new BehaviorSubject<boolean>(false);
  recordingState$ = new BehaviorSubject<'idle' | 'starting' | 'recording' | 'mic_error' | 'completed'>('idle');
  elapsedTime$ = new BehaviorSubject<string>('00:00');
  remainingTime$ = new BehaviorSubject<string>('00:00');
  extractInfo$ = new BehaviorSubject<string>('0/1');
  chunkStatus$ = new BehaviorSubject<string>('');
  canLogout$ = new BehaviorSubject<boolean>(true);
  sessionTitle$ = new BehaviorSubject<string>('Sesión');
  patientName$ = new BehaviorSubject<string>('');
  showAttendanceCheck$ = new BehaviorSubject<boolean>(false);
  attendanceCountdown$ = new BehaviorSubject<number>(120);
  auditScore$ = new BehaviorSubject<number | null>(null);
  pendingLateSession$ = new BehaviorSubject<any>(null);
  sessionGateActive$ = new BehaviorSubject<boolean>(false);
  sessionGateMode$ = new BehaviorSubject<SessionGateMode>(null);
  delayMinutes$ = new BehaviorSubject<number>(0);

  private pollSubscription?: Subscription;
  private focusHandler?: () => void;
  private recorder: MediaRecorder | null = null;
  private stream: MediaStream | null = null;
  private recordingNotification: Notification | null = null;
  private chunkTimer: any;
  private elapsedTimer: any;
  private endTimer: any;
  private attendanceCheckTimer: any;
  private attendanceCountdownInterval: any;
  private periodicAuditTimer: any;
  private recordingStartTime: number = 0;
  private chunkCount: number = 0;
  private audioChunks: Blob[] = [];
  private startedSessions: Set<number> = new Set();
  private readonly chunkIntervalMs = 5 * 60 * 1000;
  private readonly periodicAuditIntervalMs = 15 * 60 * 1000;
  private readonly pollIntervalMs = 30 * 1000;
  private currentSessionId: number | null = null;
  private pendingUploads = 0;
  private finishPending = false;
  private finishSessionId: number | null = null;
  private finishSessionTitle = '';
  private markedAbsent = false;
  private lastAutoCompleteTime = 0;

  constructor(
    private http: HttpClient,
    private zone: NgZone,
  ) {}

  iniciarPolleo() {
    this.detenerPolleo();
    this.pollSubscription = interval(this.pollIntervalMs).subscribe(() => this.checkSessions());
    this.focusHandler = () => this.checkSessions();
    window.addEventListener('focus', this.focusHandler);
    this.checkSessions();
  }

  onUserAuthenticated() {
    this.startedSessions.clear();
    this.checkSessions();
  }

  dismissLateSession(sessionId?: number) {
    void sessionId;
  }

  detenerPolleo() {
    this.pollSubscription?.unsubscribe();
    if (this.focusHandler) {
      window.removeEventListener('focus', this.focusHandler);
      this.focusHandler = undefined;
    }
  }

  private getCurrentUser(): any {
    try {
      const stored = localStorage.getItem('user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  }

  private activateSessionGate(session: any, mode: SessionGateMode, delayMinutes = 0) {
    this.currentSessionId = session.id;
    const patientName = session.patient?.name || '';
    this.sessionTitle$.next(session.title || 'Sesión');
    this.patientName$.next(patientName);
    this.activeSession$.next(session);
    this.sessionGateActive$.next(true);
    this.sessionGateMode$.next(mode);
    this.delayMinutes$.next(delayMinutes);
    if (mode === 'late') {
      this.pendingLateSession$.next(session);
    }
  }

  private checkSessions() {
    const user = this.getCurrentUser();
    if (!user || user.role !== 'terapista') {
      this.activeSession$.next(null);
      return;
    }
    if (this.recordingState$.value === 'recording') return;

    const now = Date.now();
    if (now - this.lastAutoCompleteTime > 60_000) {
      this.lastAutoCompleteTime = now;
      this.http.post('/api/sessions/auto-complete-expired', {}).subscribe({
        error: () => {},
      });
    }

    this.http.get<any>('/api/sessions/current').subscribe({
      next: (res) => {
        if (!res.success || !res.has_active) {
          if (!this.isRecording$.value && this.recordingState$.value === 'idle') {
            this.sessionGateActive$.next(false);
            this.sessionGateMode$.next(null);
            this.pendingLateSession$.next(null);
          }
          return;
        }

        const s = res.session;
        const delayMinutes = res.delay_minutes ?? 0;

        if (this.startedSessions.has(s.id) && this.recordingState$.value !== 'idle') {
          return;
        }

        if (s.status === 'scheduled' && delayMinutes >= 1 && delayMinutes <= 10) {
          if (this.sessionGateActive$.value && this.currentSessionId === s.id) return;
          this.activateSessionGate(s, 'late', delayMinutes);
          return;
        }

        if (this.startedSessions.has(s.id)) return;

        this.activateSessionGate(s, 'recording', delayMinutes);
        this.startedSessions.add(s.id);
        this.autoStart();
      },
      error: (err) => console.warn('[RecordingService] Error fetching current session:', err),
    });
  }

  confirmLateSessionStart() {
    const target = this.activeSession$.value;
    this.pendingLateSession$.next(null);
    if (!target?.id) return;
    this.startedSessions.add(target.id);
    this.sessionGateMode$.next('recording');
    this.startRecording(target);
  }

  startRecording(session: any) {
    this.currentSessionId = session.id;
    this.startedSessions.add(session.id);
    this.markedAbsent = false;
    const patientName = session.patient?.name || '';
    this.sessionTitle$.next(session.title || 'Sesión');
    this.patientName$.next(patientName);
    this.activeSession$.next(session);
    this.sessionGateActive$.next(true);
    this.sessionGateMode$.next('recording');
    this.pendingLateSession$.next(null);

    this.recordingState$.next('starting');
    this.isRecording$.next(true);
    this.canLogout$.next(false);

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      this._startRecording(stream);
    }).catch(() => {
      this.recordingState$.next('mic_error');
      this.isRecording$.next(false);
      this.canLogout$.next(false);
      this.sessionGateActive$.next(true);
    });
  }

  private autoStart() {
    this.markedAbsent = false;
    this.recordingState$.next('starting');
    this.isRecording$.next(true);
    this.canLogout$.next(false);
    this.sessionGateActive$.next(true);
    this.sessionGateMode$.next('recording');

    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
      this._startRecording(stream);
    }).catch(() => {
      this.recordingState$.next('mic_error');
      this.isRecording$.next(false);
      this.canLogout$.next(false);
      this.sessionGateActive$.next(true);
    });
  }

  retryMic() {
    const session = this.activeSession$.value;
    if (!session) return;
    this.startRecording(session);
  }

  private _startRecording(stream: MediaStream) {
    this.stream = stream;
    this.recordingState$.next('recording');
    this.sessionGateMode$.next('recording');
    this.recordingStartTime = Date.now();
    this.chunkCount = 0;
    this.startNewChunk();

    this.requestNotificationPermission();
    const patient = this.patientName$.value || 'Paciente';
    const title = this.sessionTitle$.value || 'Sesión';
    this.showRecordingNotification(
      '🔴 Grabación activa',
      `${title} — ${patient}\nLa grabación continúa aunque la pantalla esté apagada.`
    );

    if (this.currentSessionId) {
      this.http.post(`/api/sessions/${this.currentSessionId}/start-recording`, {}).subscribe();
    }

    const session = this.activeSession$.value;
    const startRaw = session?.start || session?.start_time;
    const endRaw = session?.end || session?.end_time;
    const sessionEndMs = endRaw
      ? new Date(endRaw).getTime()
      : new Date(startRaw).getTime() + 60 * 60 * 1000;
    const sessionStartMs = startRaw
      ? new Date(startRaw).getTime()
      : this.recordingStartTime;
    const totalMs = sessionEndMs - sessionStartMs;
    const totalExtracts = Math.max(1, Math.ceil(totalMs / (5 * 60 * 1000)));

    this.zone.runOutsideAngular(() => {
      this.elapsedTimer = setInterval(() => {
        const elapsed = Math.floor((Date.now() - this.recordingStartTime) / 1000);
        const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        const remaining = Math.max(0, Math.floor((sessionEndMs - Date.now()) / 1000));
        const rm = String(Math.floor(remaining / 60)).padStart(2, '0');
        const rs = String(remaining % 60).padStart(2, '0');
        const extractNum = Math.min(totalExtracts, Math.floor(elapsed / 300) + 1);
        this.zone.run(() => {
          this.elapsedTime$.next(`${m}:${s}`);
          this.remainingTime$.next(`${rm}:${rs}`);
          this.extractInfo$.next(`${extractNum}/${totalExtracts}`);
        });
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

    this.startPeriodicAudit();
    this.programarFin();
  }

  private runAttendanceCheck() {
    if (!this.currentSessionId || this.markedAbsent) return;
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
    this.markedAbsent = true;
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
      if (!this.markedAbsent) {
        this.subirChunk(blob);
      }
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
    if (!this.currentSessionId || this.markedAbsent) return;
    this.pendingUploads++;
    this.chunkStatus$.next(`Transcribiendo bloque ${this.chunkCount}...`);
    const fd = new FormData();
    fd.append('audio_file', blob, `session_${this.currentSessionId}_chunk${this.chunkCount}_${Date.now()}.webm`);
    this.http.post(`/api/sessions/${this.currentSessionId}/audio`, fd).subscribe({
      next: (data: any) => {
        this.pendingUploads--;
        if (data.success) {
          this.chunkStatus$.next(`Bloque ${this.chunkCount} transcrito`);
          const patient = this.patientName$.value || 'Paciente';
          const title = this.sessionTitle$.value || 'Sesión';
          const elapsed = this.elapsedTime$.value || '00:00';
          this.updateRecordingNotification(
            `${title} — ${patient}\nExtracto ${this.chunkCount} subido · Tiempo: ${elapsed}\nLa grabación continúa.`
          );
          this.http.post(`/api/sessions/${this.currentSessionId}/analyze-attendance`, {}).subscribe();
          this.http.get(`/api/sessions/${this.currentSessionId}/compare-live`).subscribe({
            next: (cmp: any) => {
              if (cmp.success && cmp.score_vectorial != null) {
                this.auditScore$.next(cmp.score_vectorial);
              }
            },
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
    const startRaw = session?.start || session?.start_time;
    const endRaw = session?.end || session?.end_time;
    const endTime = endRaw
      ? new Date(endRaw).getTime()
      : new Date(startRaw).getTime() + 60 * 60 * 1000;
    const timeLeft = endTime - Date.now();
    if (timeLeft > 0) {
      this.endTimer = setTimeout(() => {
        this.finishSession();
      }, timeLeft);
    }
  }

  private startPeriodicAudit() {
    this.periodicAuditTimer = setInterval(() => {
      this.runPeriodicAudit();
    }, this.periodicAuditIntervalMs);
  }

  private runPeriodicAudit() {
    if (!this.currentSessionId || this.markedAbsent) return;
    this.http.post(`/api/sessions/${this.currentSessionId}/audit-session`, {}).subscribe({
      next: () => {},
      error: () => {},
    });
  }

  private stopPeriodicAudit() {
    if (this.periodicAuditTimer) {
      clearInterval(this.periodicAuditTimer);
      this.periodicAuditTimer = null;
    }
  }

  private tryFinishAfterUpload() {
    if (this.finishPending && this.pendingUploads === 0) {
      this.finishPending = false;
      this.doFinishSession(this.finishSessionId!, this.finishSessionTitle);
    }
  }

  finishSession() {
    if (this.markedAbsent) return;
    this.finishPending = true;
    this.finishSessionId = this.currentSessionId;
    this.finishSessionTitle = this.sessionTitle$.value;
    this.stopRecording();
    this.recordingState$.next('completed');

    if (!this.finishSessionId) {
      setTimeout(() => this.closeSessionGate(), 3000);
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
                ? `Auditoría completada para "${sessionTitle}" — Puntuación: ${score}/100`
                : `Auditoría completada para "${sessionTitle}"`;
              this.http.post(`/api/notifications/create`, { message: msg }).subscribe();
            }
          },
          error: () => {
            this.http.post(`/api/notifications/create`, {
              message: `Auditoría disponible para "${sessionTitle}" (revisar manualmente)`,
            }).subscribe();
          },
        });
        setTimeout(() => this.closeSessionGate(), 4000);
      },
      error: () => {
        setTimeout(() => this.closeSessionGate(), 4000);
      },
    });
  }

  markNoShow(sessionId?: number) {
    const id = sessionId || this.currentSessionId;
    if (!id) return;
    this.http.post(`/api/sessions/${id}/mark-absent`, {}).subscribe({
      next: () => this.closeSessionGate(),
      error: () => this.closeSessionGate(),
    });
  }

  stopRecording() {
    this.isRecording$.next(false);
    clearInterval(this.chunkTimer);
    clearInterval(this.elapsedTimer);
    clearTimeout(this.endTimer);
    clearTimeout(this.attendanceCheckTimer);
    this.stopPeriodicAudit();
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

  private closeSessionGate() {
    this.stopRecording();
    this.closeRecordingNotification();
    this.activeSession$.next(null);
    this.recordingState$.next('idle');
    this.currentSessionId = null;
    this.sessionGateActive$.next(false);
    this.sessionGateMode$.next(null);
    this.pendingLateSession$.next(null);
    this.showAttendanceCheck$.next(false);
    this.auditScore$.next(null);
    this.canLogout$.next(true);
    this.markedAbsent = false;
  }

  forceStopAndLogout() {
    this.closeSessionGate();
    this.startedSessions.clear();
  }

  getLateDelayLabel(): string {
    const mins = this.delayMinutes$.value;
    if (mins <= 0) return 'menos de 1 min';
    return `${mins} min`;
  }

  private requestNotificationPermission() {
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }

  private showRecordingNotification(title: string, body: string) {
    if (!('Notification' in window) || Notification.permission !== 'granted') return;
    try {
      this.recordingNotification?.close();
      this.recordingNotification = new Notification(title, {
        body,
        icon: '/assets/img/logo.svg',
        tag: 'recording-session',
        requireInteraction: true,
        silent: false,
      } as any);
      this.recordingNotification.onclick = () => {
        window.focus();
        this.recordingNotification?.close();
      };
    } catch {
      // Mobile browsers may not support all options
    }
  }

  private updateRecordingNotification(body: string) {
    if (this.recordingNotification) {
      try {
        this.recordingNotification.close();
      } catch { /* ignore */ }
    }
    this.showRecordingNotification('🔴 Grabación activa', body);
  }

  private closeRecordingNotification() {
    if (this.recordingNotification) {
      try {
        this.recordingNotification.close();
      } catch { /* ignore */ }
      this.recordingNotification = null;
    }
  }
}
