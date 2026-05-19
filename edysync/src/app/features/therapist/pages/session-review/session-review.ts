import { Component, OnInit, OnDestroy, ChangeDetectorRef, NgZone } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService } from '../../../../core/services/therapist.service';
import { AlertService } from '../../../../core/services/alert.service';
import { RecordingService } from '../../../../core/services/recording.service';
import { ConfirmService } from '../../../../core/services/confirm.service';

@Component({
  selector: 'app-therapist-session-review',
  standalone: false,
  templateUrl: './session-review.html',
  styleUrl: './session-review.scss',
})
export class TherapistSessionReview implements OnInit, OnDestroy {

  // Session
  session: any = null;
  sessionId = 0;
  loading = true;
  saving = false;

  // Notes
  notes = '';
  private saveTimeout: any = null;
  lastSavedLabel = 'Sin cambios pendientes';

  // Attendance
  attendance: string | null = null;

  // Images
  images: any[] = [];
  currentImage: any = null;
  currentImageIndex = 0;
  uploadingImage = false;
  showCameraModal = false;
  private videoStream: MediaStream | null = null;

  // Audio Recording
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private audioStream: MediaStream | null = null;
  private recordingStartTime: number | null = null;
  private recordingTimerInterval: any = null;
  private chunkTimer: any = null;
  isRecording = false;
  accumulatedTranscript = '';
  chunkCount = 0;
  recordingElapsed = '00:00';
  uploadingChunk = false;
  chunkUploadStatus = '';
  autoStarted = false;

  // No-Show Warning Timer
  showWarningModal = false;
  warningCountdown = 1200;
  private warningInterval: any = null;
  private lastAttendanceCheck: number | null = null;

  // Audit
  audit: any = null;
  auditLoading = false;
  auditRunning = false;

  // Feedback
  feedbackEngagement: number | null = null;
  feedbackProgress: number | null = null;
  feedbackNotes = '';
  feedbackSaving = false;
  feedbackSubmitted = false;

  // Program Modal
  showProgramModal = false;
  programText = '';
  programUploadedAt = '';
  programLoading = false;

  // Fullscreen
  showFullscreen = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private therapistService: TherapistService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
    private ngZone: NgZone,
    private alertService: AlertService,
    private recordingService: RecordingService,
    private confirmService: ConfirmService,
  ) {}

  ngOnInit() {
    this.sessionId = Number(this.route.snapshot.paramMap.get('id'));
    if (!this.sessionId) {
      this.router.navigate(['/therapist/sessions']);
      return;
    }
    this.loadSession();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.stopRecording();
    this.clearWarningTimer();
    if (this.saveTimeout) clearTimeout(this.saveTimeout);
    if (this.videoStream) this.videoStream.getTracks().forEach(t => t.stop());
  }

  private loadSession() {
    this.loading = true;
    this.headerService.setConfig({
      title: 'Revisión de Sesión',
      subtitle: 'Cargando...',
      icon: ['fas', 'clipboard-check'],
    });

    this.therapistService.getSession(this.sessionId).subscribe({
      next: (data) => {
        this.session = data;
        this.notes = data.notes || '';
        this.attendance = data.attendance || null;
        this.images = data.images || [];
        if (this.images.length > 0) this.currentImage = this.images[0];
        this.loading = false;

        this.headerService.setConfig({
          title: 'Revisión de Sesión',
          subtitle: `${data.patient?.name || 'Paciente'} - ${data.title || 'Sesión'}`,
          icon: ['fas', 'clipboard-check'],
        });

        this.loadAudit();
        this.loadProgram();
        this.maybeAutoStartRecording();
      },
      error: () => {
        this.loading = false;
        this.router.navigate(['/therapist/sessions']);
      },
    });
  }

  private maybeAutoStartRecording() {
    if (!this.session || this.autoStarted) return;

    // Already recording globally via RecordingService
    if (this.recordingService.isRecording$.value && this.recordingService.activeSession$.value?.id === this.sessionId) {
      this.autoStarted = true;
      this.isRecording = true;
      this.recordingService.elapsedTime$.subscribe(t => this.recordingElapsed = t);
      this.recordingService.chunkStatus$.subscribe(s => this.chunkUploadStatus = s);
      return;
    }

    if (this.session.status === 'scheduled' || this.session.status === 'in_progress') {
      const now = new Date();
      const start = new Date(this.session.start_time);
      const end = this.session.end_time ? new Date(this.session.end_time) : new Date(start.getTime() + 60 * 60 * 1000);

      if (start <= now && now <= end && this.attendance !== 'absent') {
        this.autoStarted = true;
        this.therapistService.startRecording(this.sessionId).subscribe({
          next: () => {
            this.startRecording();
          },
          error: () => {
            // Silently fail - user can still click record
          }
        });
      }
    }
  }

  setAttendance(state: string) {
    this.attendance = state;
    this.therapistService.updateAttendance(this.sessionId, state).subscribe();
    if (state === 'present') {
      this.clearWarningTimer();
      this.showWarningModal = false;
    }
  }

  onNotesInput() {
    this.lastSavedLabel = 'Escribiendo...';
    if (this.saveTimeout) clearTimeout(this.saveTimeout);
    this.saveTimeout = setTimeout(() => this.saveNotes(), 2000);
    this.clearWarningTimer();
  }

  saveNotes() {
    this.saving = true;
    this.therapistService.saveNotes(this.sessionId, this.notes).subscribe({
      next: () => {
        this.saving = false;
        this.lastSavedLabel = 'Guardado a las ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        setTimeout(() => {
          if (this.lastSavedLabel.includes('Guardado')) {
            this.lastSavedLabel = 'Sin cambios pendientes';
          }
        }, 3000);
      },
      error: () => {
        this.saving = false;
        this.lastSavedLabel = 'Error al guardar';
      },
    });
  }

  onImageSelected(event: any) {
    const file = event.target.files?.[0];
    if (!file) return;
    this.uploadImage(file);
    event.target.value = null;
  }

  uploadImage(file: File) {
    this.uploadingImage = true;
    this.therapistService.uploadSessionImage(this.sessionId, file).subscribe({
      next: (res) => {
        this.uploadingImage = false;
        if (res.success) {
          this.images.push(res.image);
          this.currentImage = res.image;
          this.clearWarningTimer();
        }
      },
      error: () => {
        this.uploadingImage = false;
      },
    });
  }

  selectImage(img: any) {
    this.currentImage = img;
    this.currentImageIndex = this.images.indexOf(img);
  }

  async deleteCurrentImage() {
    if (!this.currentImage) return;
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar imagen',
      message: '¿Estás seguro de eliminar esta imagen?',
      confirmText: 'Eliminar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.therapistService.deleteSessionImage(this.sessionId, this.currentImage.id).subscribe({
      next: (res) => {
        if (res.success) {
          const idx = this.images.indexOf(this.currentImage);
          this.images = this.images.filter((i: any) => i.id !== this.currentImage.id);
          this.currentImage = this.images.length > 0 ? this.images[Math.min(idx, this.images.length - 1)] : null;
        }
      },
    });
  }

  async openCamera() {
    try {
      this.videoStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      this.showCameraModal = true;
      setTimeout(() => {
        const video = document.getElementById('cameraVideo') as HTMLVideoElement;
        if (video) video.srcObject = this.videoStream;
      }, 100);
    } catch {
      this.alertService.show('No se pudo acceder a la cámara. Verifica los permisos.', 'error');
    }
  }

  closeCamera() {
    this.showCameraModal = false;
    if (this.videoStream) {
      this.videoStream.getTracks().forEach(t => t.stop());
      this.videoStream = null;
    }
  }

  takePhoto() {
    const video = document.getElementById('cameraVideo') as HTMLVideoElement;
    if (!video || video.readyState < video.HAVE_ENOUGH_DATA) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d')!.drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob) {
        const file = new File([blob], `capture_${Date.now()}.jpg`, { type: 'image/jpeg' });
        this.closeCamera();
        this.uploadImage(file);
      }
    }, 'image/jpeg', 0.85);
  }

  toggleRecording() {
    if (this.isRecording) {
      this.stopRecording(true);
    } else {
      this.startRecording();
      if (!this.autoStarted) {
        this.therapistService.startRecording(this.sessionId).subscribe();
      }
    }
  }

  private startRecording() {
    this.isRecording = true;
    this.chunkCount = 0;
    this.accumulatedTranscript = '';
    this.recordingElapsed = '00:00';
    this.chunkUploadStatus = '';
    this.cdr.detectChanges();

    navigator.mediaDevices.getUserMedia({ audio: true })
      .then((stream) => {
        this.audioStream = stream;
        this.recordingStartTime = Date.now();
        this.startNewChunk();

        this.ngZone.runOutsideAngular(() => {
          this.recordingTimerInterval = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.recordingStartTime!) / 1000);
            const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
            const secs = String(elapsed % 60).padStart(2, '0');
            this.recordingElapsed = `${mins}:${secs}`;
            this.cdr.detectChanges();
          }, 1000);

          this.chunkTimer = setInterval(() => {
            if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
              this.mediaRecorder.stop();
            }
          }, 5 * 60 * 1000);
        });
      })
      .catch(() => {
        this.isRecording = false;
        this.cdr.detectChanges();
        this.alertService.show('No se pudo acceder al micrófono. Verifica los permisos.', 'error');
      });
  }

  private getSupportedMimeType(): string {
    const types = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4'];
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t;
    }
    return '';
  }

  private startNewChunk() {
    this.audioChunks = [];
    const mimeType = this.getSupportedMimeType();
    this.mediaRecorder = new MediaRecorder(this.audioStream!, mimeType ? { mimeType } : {});

    this.mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) this.audioChunks.push(e.data);
    };

    this.mediaRecorder.onstop = () => {
      this.chunkCount++;
      const blob = new Blob(this.audioChunks, { type: this.mediaRecorder?.mimeType || 'audio/webm' });
      this.uploadAudioChunk(blob, this.chunkCount);
      if (this.isRecording && this.audioStream?.active) {
        this.startNewChunk();
      }
    };

    this.mediaRecorder.start(1000);
  }

  private stopRecording(fromDestroy = false) {
    this.isRecording = false;
    this.ngZone.runOutsideAngular(() => {
      clearInterval(this.chunkTimer);
      clearInterval(this.recordingTimerInterval);
    });
    this.chunkTimer = null;
    this.recordingTimerInterval = null;

    if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
      this.mediaRecorder.stop();
    }
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(t => t.stop());
      this.audioStream = null;
    }
    this.clearWarningTimer();
    if (!fromDestroy) this.cdr.detectChanges();
  }

  private uploadAudioChunk(blob: Blob, chunkNum: number) {
    this.uploadingChunk = true;
    this.chunkUploadStatus = `Transcribiendo segmento ${chunkNum}...`;

    this.therapistService.uploadAudioChunk(this.sessionId, blob, chunkNum).subscribe({
      next: (data) => {
        this.uploadingChunk = false;
        if (data.success && data.transcript_text) {
          this.accumulatedTranscript += (this.accumulatedTranscript ? ' ' : '') + data.transcript_text;
          this.chunkUploadStatus = `Segmento ${chunkNum} transcrito`;

          if (!this.isRecording) {
            if (this.accumulatedTranscript) {
              const separator = this.notes.trim() ? '\n\n--- Transcripción de sesión ---\n\n' : '';
              this.notes = this.notes.trimEnd() + separator + this.accumulatedTranscript;
              setTimeout(() => this.saveNotes(), 500);
            }
            this.chunkUploadStatus = 'Grabacion completa. Audio eliminado.';
            setTimeout(() => {
              this.chunkUploadStatus = '';
              this.loadAudit();
            }, 3000);
          } else {
            setTimeout(() => { this.chunkUploadStatus = ''; }, 2000);
            this.checkAttendance();
          }
        } else {
          this.chunkUploadStatus = `Error: ${data.error || 'desconocido'}`;
        }
      },
      error: () => {
        this.uploadingChunk = false;
        this.chunkUploadStatus = 'Error de conexión';
      },
    });
  }

  private checkAttendance() {
    this.therapistService.analyzeAttendance(this.sessionId).subscribe({
      next: (data) => {
        if (data.success && data.suggested_attendance === 'absent' && this.attendance !== 'present') {
          this.startWarningTimer(data.reason || 'Sin actividad detectada');
        }
      },
      error: () => {}
    });
  }

  private startWarningTimer(reason: string) {
    if (this.showWarningModal) return;

    this.showWarningModal = true;
    this.warningCountdown = 1200;
    this.lastAttendanceCheck = Date.now();

    setTimeout(() => {
      if (this.showWarningModal && this.warningCountdown <= 0) {
        this.markAbsent();
      }
    }, 20 * 60 * 1000);

    this.ngZone.runOutsideAngular(() => {
      this.warningInterval = setInterval(() => {
        this.warningCountdown--;
        if (this.warningCountdown <= 0) {
          this.clearWarningTimer();
        }
      }, 1000);
    });
  }

  private clearWarningTimer() {
    if (this.warningInterval) {
      clearInterval(this.warningInterval);
      this.warningInterval = null;
    }
  }

  dismissWarning() {
    this.clearWarningTimer();
    this.showWarningModal = false;
  }

  markAbsent() {
    this.therapistService.markAbsent(this.sessionId).subscribe({
      next: () => {
        this.attendance = 'absent';
        this.session.status = 'completed';
        this.stopRecording();
        this.showWarningModal = false;
        this.clearWarningTimer();
        this.alertService.show('Sesión marcada como ausente.', 'info');
      },
    });
  }

  get warningTimeLeft(): string {
    const mins = Math.floor(this.warningCountdown / 60);
    const secs = this.warningCountdown % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  }

  loadAudit() {
    this.auditLoading = true;
    this.therapistService.getSessionAudit(this.sessionId).subscribe({
      next: (data) => {
        this.auditLoading = false;
        if (data.success && data.exists) {
          this.audit = data.audit;
          this.feedbackEngagement = data.audit.feedback_engagement || null;
          this.feedbackProgress = data.audit.feedback_progress || null;
          this.feedbackNotes = data.audit.feedback_notes || '';
          this.feedbackSubmitted = !!(data.audit.feedback_engagement || data.audit.feedback_progress);
        } else {
          this.audit = null;
        }
      },
      error: () => {
        this.auditLoading = false;
        this.audit = null;
      },
    });
  }

  triggerAudit() {
    this.auditRunning = true;
    this.therapistService.triggerAudit(this.sessionId).subscribe({
      next: (data) => {
        this.auditRunning = false;
        if (data.success) {
          this.loadAudit();
        }
      },
      error: () => {
        this.auditRunning = false;
      },
    });
  }

  get auditStatusText(): string {
    if (!this.audit) return 'Sin datos';
    const m: any = {
      pending: { text: 'Pendiente', cls: 'bg-yellow-100 text-yellow-700' },
      processing: { text: 'Procesando...', cls: 'bg-blue-100 text-blue-700' },
      completed: { text: `Score: ${this.audit.audit_score}%`, cls: this.getScoreClass(this.audit.audit_score) },
      error: { text: 'Error', cls: 'bg-red-100 text-red-700' },
    };
    return m[this.audit.audit_status]?.text || m.pending.text;
  }

  get auditStatusClass(): string {
    if (!this.audit) return 'bg-surface-container text-on-surface-variant';
    const m: any = {
      pending: 'bg-yellow-100 text-yellow-700',
      processing: 'bg-blue-100 text-blue-700',
      completed: this.getScoreClass(this.audit.audit_score),
      error: 'bg-red-100 text-red-700',
    };
    return m[this.audit.audit_status] || m.pending;
  }

  private getScoreClass(score: number): string {
    if (score >= 80) return 'bg-green-100 text-green-700';
    if (score >= 50) return 'bg-yellow-100 text-yellow-700';
    return 'bg-red-100 text-red-700';
  }

  get gaugeColor(): string {
    if (!this.audit?.audit_score) return '#e5e7eb';
    const score = this.audit.audit_score;
    if (score >= 80) return '#10b981';
    if (score >= 50) return '#f59e0b';
    return '#ef4444';
  }

  get report(): any {
    return this.audit?.report || null;
  }

  get classificationLabel(): string {
    const m: any = { cumple: 'Cumple', cumple_parcial: 'Cumple Parcial', no_cumple: 'No Cumple' };
    return m[this.report?.status] || this.report?.status || '';
  }

  get classificationColor(): string {
    const m: any = { cumple: 'text-green-600', cumple_parcial: 'text-yellow-600', no_cumple: 'text-red-600' };
    return m[this.report?.status] || 'text-on-surface-variant';
  }

  objectiveClass(cls: string): string {
    const m: any = {
      logrado: 'bg-green-50 border-green-200 text-green-800',
      parcial: 'bg-yellow-50 border-yellow-200 text-yellow-800',
      no_cubierto: 'bg-red-50 border-red-200 text-red-800',
    };
    return m[cls] || 'bg-surface-container-low border-outline-variant';
  }

  objectiveIcon(cls: string): string {
    const m: any = {
      logrado: 'fa-check-circle text-green-500',
      parcial: 'fa-exclamation-circle text-yellow-500',
      no_cubierto: 'fa-times-circle text-red-500',
    };
    return m[cls] || 'fa-question-circle text-on-surface-variant';
  }

  submitFeedback() {
    if (this.feedbackSubmitted) return;
    this.feedbackSaving = true;
    this.therapistService.submitFeedback(this.sessionId, {
      engagement: this.feedbackEngagement,
      progress: this.feedbackProgress,
      notes: this.feedbackNotes,
    }).subscribe({
      next: () => {
        this.feedbackSaving = false;
        this.feedbackSubmitted = true;
      },
      error: () => {
        this.feedbackSaving = false;
      },
    });
  }

  setEngagement(val: number) {
    this.feedbackEngagement = val;
  }

  setProgress(val: number) {
    this.feedbackProgress = val;
  }

  loadProgram() {
    this.therapistService.getSessionProgram(this.sessionId).subscribe({
      next: (data) => {
        if (data.success && data.exists) {
          this.programText = data.planned_text;
          this.programUploadedAt = data.uploaded_at;
        }
      },
    });
  }

  openProgramModal() {
    this.showProgramModal = true;
    this.programLoading = true;
    this.therapistService.getSessionProgram(this.sessionId).subscribe({
      next: (data) => {
        this.programLoading = false;
        if (data.success && data.exists) {
          this.programText = data.planned_text;
          this.programUploadedAt = data.uploaded_at;
        } else {
          this.programText = '';
        }
      },
      error: () => {
        this.programLoading = false;
        this.programText = '';
      },
    });
  }

  closeProgramModal() {
    this.showProgramModal = false;
  }

  formatProgramText(text: string): string {
    if (!text) return '';
    return text
      .replace(/\n/g, '<br>')
      .replace(/<br>## /g, '</p><h3>')
      .replace(/<br>\[TABLA\]<br>/g, '<div class="table-wrap"><table>')
      .replace(/<br>\[\/TABLA\]/g, '</table></div>')
      .split('<br>').map(line => {
        if (line.startsWith('<h3')) return line + '</h3>';
        if (line.includes(' | ')) {
          const cells = line.split(' | ').map(c => `<td>${c}</td>`).join('');
          return `<tr>${cells}</tr>`;
        }
        return line.trim() ? `<p>${line}</p>` : '';
      }).join('\n');
  }

  printProgram() {
    const content = document.getElementById('programPrintContent');
    if (!content) return;
    const win = window.open('', '_blank');
    win!.document.write(`
      <html><head><title>Programación de Sesión</title>
      <style>
        body { font-family: Arial, sans-serif; padding: 2rem; color: #333; line-height: 1.6; }
        h3 { color: #6b21a8; margin-top: 1.5rem; }
        table { width: 100%; border-collapse: collapse; margin: 0.5rem 0; }
        td { border: 1px solid #ccc; padding: 4px 8px; }
        p { margin: 4px 0; }
        @media print { body { padding: 1rem; } }
      </style></head>
      <body>
        <h2 style="color:#6b21a8;border-bottom:2px solid #6b21a8;padding-bottom:0.5rem;">Programación de Sesión</h2>
        ${content.innerHTML}
      </body></html>
    `);
    win!.document.close();
    win!.focus();
    win!.print();
  }

  openFullscreen() {
    this.showFullscreen = true;
  }

  closeFullscreen() {
    this.showFullscreen = false;
  }

  get hasProgram(): boolean {
    return !!(this.audit?.has_program || this.programText);
  }

  get programPreview(): string {
    if (!this.programText) return '';
    return this.programText.substring(0, 200) + (this.programText.length > 200 ? '...' : '');
  }
}
