import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, NgZone } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, Subscription } from 'rxjs';
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
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TherapistSessionReview implements OnInit, OnDestroy {

  session: any = null;
  sessionId = 0;
  loading = true;
  saving = false;
  error: string | null = null;

  notes = '';
  private saveTimeout: any = null;
  lastSavedLabel = 'Sin cambios pendientes';

  attendance: string | null = null;

  images: any[] = [];
  currentImage: any = null;
  currentImageIndex = 0;
  uploadingImage = false;
  showCameraModal = false;
  private videoStream: MediaStream | null = null;

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

  private pendingAutoAudit = false;

  showWarningModal = false;
  warningCountdown = 1200;
  private warningInterval: any = null;
  private lastAttendanceCheck: number | null = null;

  audit: any = null;
  auditLoading = false;
  auditRunning = false;

  feedbackEngagement: number | null = null;
  feedbackProgress: number | null = null;
  feedbackNotes = '';
  feedbackSaving = false;
  feedbackSubmitted = false;

  liveScore: number | null = null;
  private liveScoreSub: Subscription | null = null;

  showProgramModal = false;
  programText = '';
  programUploadedAt = '';
  programLoading = false;

  showFullscreen = false;

  private subs = new Subscription();

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private http: HttpClient,
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
    this.liveScoreSub?.unsubscribe();
    this.subs.unsubscribe();
    if (this.saveTimeout) clearTimeout(this.saveTimeout);
    if (this.videoStream) this.videoStream.getTracks().forEach(t => t.stop());
  }

  private loadSession() {
    this.loading = true;
    this.cdr.markForCheck();
    this.headerService.setConfig({
      title: 'Revisión de Sesión',
      subtitle: 'Cargando...',
      icon: ['fas', 'clipboard-check'],
    });

    this.subs.add(this.therapistService.getSession(this.sessionId).subscribe({
      next: (data) => {
        this.session = data;
        this.notes = data.notes || '';
        this.attendance = data.attendance || null;
        this.images = data.images || [];
        if (this.images.length > 0) this.currentImage = this.images[0];
        this.loading = false;
        this.cdr.markForCheck();

        this.headerService.setConfig({
          title: 'Revisión de Sesión',
          subtitle: `${data.patient?.name || 'Paciente'} - ${data.title || 'Sesión'}`,
          icon: ['fas', 'clipboard-check'],
        });

        this.loadAudit();
        this.loadProgram();
        this.initLiveScore();
        this.maybeAutoStartRecording();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
        this.router.navigate(['/therapist/sessions']);
      },
    }));
  }

  private maybeAutoStartRecording() {
    if (!this.session || this.autoStarted) return;

    if (this.recordingService.isRecording$.value && this.recordingService.activeSession$.value?.id === this.sessionId) {
      this.autoStarted = true;
      this.isRecording = true;
      this.subs.add(this.recordingService.elapsedTime$.subscribe(t => {
        this.recordingElapsed = t;
        this.cdr.markForCheck();
      }));
      this.subs.add(this.recordingService.chunkStatus$.subscribe(s => {
        this.chunkUploadStatus = s;
        this.cdr.markForCheck();
      }));
      return;
    }

    if (this.session.status === 'scheduled' || this.session.status === 'in_progress') {
      const now = new Date();
      const start = new Date(this.session.start_time);
      const end = this.session.end_time ? new Date(this.session.end_time) : new Date(start.getTime() + 60 * 60 * 1000);

      if (start <= now && now <= end && this.attendance !== 'absent') {
        this.autoStarted = true;
        this.subs.add(this.therapistService.startRecording(this.sessionId).subscribe({
          next: () => {
            this.startRecording();
          },
          error: (err) => {
            this.error = err.message;
            this.cdr.markForCheck();
          }
        }));
      }
    }
  }

  setAttendance(state: string) {
    this.attendance = state;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.updateAttendance(this.sessionId, state).subscribe({
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      }
    }));
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
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.saveNotes(this.sessionId, this.notes).subscribe({
      next: () => {
        this.saving = false;
        this.lastSavedLabel = 'Guardado a las ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        this.cdr.markForCheck();
        setTimeout(() => {
          if (this.lastSavedLabel.includes('Guardado')) {
            this.lastSavedLabel = 'Sin cambios pendientes';
            this.cdr.markForCheck();
          }
        }, 3000);
      },
      error: (err) => {
        this.saving = false;
        this.error = err.message;
        this.lastSavedLabel = 'Error al guardar';
        this.cdr.markForCheck();
      },
    }));
  }

  onImageSelected(event: any) {
    const file = event.target.files?.[0];
    if (!file) return;
    this.uploadImage(file);
    event.target.value = null;
  }

  uploadImage(file: File) {
    this.uploadingImage = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.uploadSessionImage(this.sessionId, file).subscribe({
      next: (res) => {
        this.uploadingImage = false;
        if (res.success) {
          this.images.push(res.image);
          this.currentImage = res.image;
          this.clearWarningTimer();
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.uploadingImage = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
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
    this.subs.add(this.therapistService.deleteSessionImage(this.sessionId, this.currentImage.id).subscribe({
      next: (res) => {
        if (res.success) {
          const idx = this.images.indexOf(this.currentImage);
          this.images = this.images.filter((i: any) => i.id !== this.currentImage.id);
          this.currentImage = this.images.length > 0 ? this.images[Math.min(idx, this.images.length - 1)] : null;
          this.cdr.markForCheck();
        }
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  async openCamera() {
    try {
      this.videoStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      });
      this.showCameraModal = true;
      this.cdr.markForCheck();
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
        this.subs.add(this.therapistService.startRecording(this.sessionId).subscribe({
          error: (err) => {
            this.error = err.message;
            this.cdr.markForCheck();
          }
        }));
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
      this.subirChunkAudio(blob, this.chunkCount);
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

  private subirChunkAudio(blob: Blob, chunkNum: number, retriesRemaining = 3) {
    this.uploadingChunk = true;
    this.chunkUploadStatus = `Transcribiendo segmento ${chunkNum}...`;
    this.cdr.markForCheck();

    this.subs.add(this.therapistService.uploadAudioChunk(this.sessionId, blob, chunkNum).subscribe({
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
            this.pendingAutoAudit = true;
            setTimeout(() => {
              this.chunkUploadStatus = '';
              this.cdr.markForCheck();
              this.loadAudit();
            }, 3000);
          } else {
            setTimeout(() => { this.chunkUploadStatus = ''; this.cdr.markForCheck(); }, 2000);
            this.checkAttendance();
          }
        } else {
          this.chunkUploadStatus = `Error: ${data.error || 'desconocido'}`;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        if (retriesRemaining > 1) {
          this.chunkUploadStatus = `Reintentando segmento ${chunkNum}...`;
          this.cdr.markForCheck();
          setTimeout(() => this.subirChunkAudio(blob, chunkNum, retriesRemaining - 1), 2000);
        } else {
          this.uploadingChunk = false;
          this.error = err.message;
          this.chunkUploadStatus = 'Error de conexión';
          this.cdr.markForCheck();
        }
      },
    }));
  }

  private checkAttendance() {
    this.subs.add(this.therapistService.analyzeAttendance(this.sessionId).subscribe({
      next: (data) => {
        if (data.success && data.suggested_attendance === 'absent' && this.attendance !== 'present') {
          this.startWarningTimer(data.reason || 'Sin actividad detectada');
        }
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      }
    }));
  }

  private startWarningTimer(reason: string) {
    if (this.showWarningModal) return;

    this.showWarningModal = true;
    this.warningCountdown = 1200;
    this.lastAttendanceCheck = Date.now();
    this.cdr.markForCheck();

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
    this.subs.add(this.therapistService.markAbsent(this.sessionId).subscribe({
      next: () => {
        this.attendance = 'absent';
        this.session.status = 'completed';
        this.stopRecording();
        this.showWarningModal = false;
        this.clearWarningTimer();
        this.cdr.markForCheck();
        this.alertService.show('Sesión marcada como ausente.', 'info');
        this.loadAudit();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  get warningTimeLeft(): string {
    const mins = Math.floor(this.warningCountdown / 60);
    const secs = this.warningCountdown % 60;
    return `${mins}:${String(secs).padStart(2, '0')}`;
  }

  loadAudit() {
    this.auditLoading = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getSessionAudit(this.sessionId).subscribe({
      next: (data) => {
        this.auditLoading = false;
        if (data.success && data.exists) {
          this.audit = data.audit;
          this.feedbackEngagement = data.audit.feedback_engagement || null;
          this.feedbackProgress = data.audit.feedback_progress || null;
          this.feedbackNotes = data.audit.feedback_notes || '';
          this.feedbackSubmitted = !!(data.audit.feedback_engagement || data.audit.feedback_progress);
          if (this.pendingAutoAudit && data.audit.has_program && data.audit.has_transcript && data.audit.audit_status === 'pending') {
            this.pendingAutoAudit = false;
            this.triggerAudit();
          } else if (this.pendingAutoAudit) {
            this.pendingAutoAudit = false;
            if (!data.audit.has_program) {
              this.alertService.show('No se puede auditar: no hay programación (.docx) subida para esta sesión.', 'warning');
            } else if (!data.audit.has_transcript) {
              this.alertService.show('No se puede auditar: no hay transcripción de audio disponible.', 'warning');
            }
          }
        } else {
          this.audit = null;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.auditLoading = false;
        this.error = err.message;
        this.audit = null;
        this.cdr.markForCheck();
      },
    }));
  }

  private initLiveScore() {
    this.liveScoreSub?.unsubscribe();
    this.subs.add(this.http.get(`/api/sessions/${this.sessionId}/compare-live`).subscribe({
      next: (res: any) => {
        if (res.success) this.liveScore = res.score_vectorial;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      }
    }));
    this.liveScoreSub = this.recordingService.auditScore$.subscribe(score => {
      this.liveScore = score;
      this.cdr.markForCheck();
    });
  }

  triggerAudit() {
    this.auditRunning = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.triggerAudit(this.sessionId).subscribe({
      next: (data) => {
        this.auditRunning = false;
        if (data.success) {
          this.loadAudit();
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.auditRunning = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  downloadDocx() {
    this.subs.add(this.therapistService.downloadReportDocx(this.sessionId).subscribe({
      next: (blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `auditoria_${this.sessionId}.docx`;
        a.click();
        window.URL.revokeObjectURL(url);
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
        this.alertService.show('Error al descargar el reporte', 'error');
      },
    }));
  }

  get auditStatusText(): string {
    if (!this.audit) return 'Sin datos';
    const m: any = {
      pending: 'Pendiente',
      processing: 'Procesando...',
      completed: `Score: ${this.audit.audit_score}%`,
      error: 'Error',
    };
    return m[this.audit.audit_status] || m.pending;
  }

  get report(): any {
    return this.audit?.report || null;
  }

  get classificationLabel(): string {
    const m: any = { cumple: 'Cumple', cumple_parcial: 'Cumple Parcial', no_cumple: 'No Cumple' };
    return m[this.report?.status] || this.report?.status || '';
  }

  submitFeedback() {
    if (this.feedbackSubmitted) return;
    this.feedbackSaving = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.submitFeedback(this.sessionId, {
      engagement: this.feedbackEngagement,
      progress: this.feedbackProgress,
      notes: this.feedbackNotes,
    }).subscribe({
      next: () => {
        this.feedbackSaving = false;
        this.feedbackSubmitted = true;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.feedbackSaving = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  setEngagement(val: number) {
    this.feedbackEngagement = val;
  }

  setProgress(val: number) {
    this.feedbackProgress = val;
  }

  loadProgram() {
    this.subs.add(this.therapistService.getSessionProgram(this.sessionId).subscribe({
      next: (data) => {
        if (data.success && data.exists) {
          this.programText = data.planned_text;
          this.programUploadedAt = data.uploaded_at;
          this.cdr.markForCheck();
        }
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  openProgramModal() {
    this.showProgramModal = true;
    this.programLoading = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getSessionProgram(this.sessionId).subscribe({
      next: (data) => {
        this.programLoading = false;
        if (data.success && data.exists) {
          this.programText = data.planned_text;
          this.programUploadedAt = data.uploaded_at;
        } else {
          this.programText = '';
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.programLoading = false;
        this.error = err.message;
        this.programText = '';
        this.cdr.markForCheck();
      },
    }));
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
        <h2 style="color:var(--color-accent);border-bottom:2px solid var(--color-accent);padding-bottom:0.5rem;">Programación de Sesión</h2>
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
