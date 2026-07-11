import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService } from '../../../../core/services/therapist.service';
import { ToastService } from '../../../../core/services/toast.service';
import { RecordingService } from '../../../../core/services/recording.service';
import { ConfirmService } from '../../../../core/services/confirm.service';

@Component({
  selector: 'app-therapist-session-review',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule],
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

  isRecording = false;
  recordingElapsed = '00:00';
  chunkUploadStatus = '';
  chunkCount = 0;

  showWarningModal = false;
  warningCountdown = 1200;
  private warningInterval: any = null;

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
    private toastService: ToastService,
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
    this.subscribeToRecordingService();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.clearWarningTimer();
    this.liveScoreSub?.unsubscribe();
    this.subs.unsubscribe();
    if (this.saveTimeout) clearTimeout(this.saveTimeout);
    if (this.videoStream) this.videoStream.getTracks().forEach(t => t.stop());
  }

  private subscribeToRecordingService() {
    this.subs.add(this.recordingService.isRecording$.subscribe(recording => {
      this.isRecording = recording;
      this.cdr.markForCheck();
    }));
    this.subs.add(this.recordingService.elapsedTime$.subscribe(time => {
      this.recordingElapsed = time;
      this.cdr.markForCheck();
    }));
    this.subs.add(this.recordingService.chunkStatus$.subscribe(status => {
      this.chunkUploadStatus = status;
      this.cdr.markForCheck();
    }));
    this.subs.add(this.recordingService.auditScore$.subscribe(score => {
      this.liveScore = score;
      this.cdr.markForCheck();
    }));
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
    if (!this.session) return;

    if (this.recordingService.isRecording$.value && this.recordingService.activeSession$.value?.id === this.sessionId) {
      return;
    }

    if (this.session.status === 'scheduled' || this.session.status === 'in_progress') {
      const now = new Date();
      const start = new Date(this.session.start_time);
      const end = this.session.end_time ? new Date(this.session.end_time) : new Date(start.getTime() + 60 * 60 * 1000);

      if (start <= now && now <= end && this.attendance !== 'absent') {
        this.subs.add(this.therapistService.startRecording(this.sessionId).subscribe({
          next: () => {
            this.recordingService.startRecording(this.session);
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
      this.toastService.show('No se pudo acceder a la cámara. Verifica los permisos.', 'error');
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
      this.recordingService.finishSession();
    } else {
      this.subs.add(this.therapistService.startRecording(this.sessionId).subscribe({
        next: () => {
          this.recordingService.startRecording(this.session);
        },
        error: (err) => {
          this.error = err.message;
          this.cdr.markForCheck();
        }
      }));
    }
  }

  private startWarningTimer(reason: string) {
    if (this.showWarningModal) return;

    this.showWarningModal = true;
    this.warningCountdown = 1200;
    this.cdr.markForCheck();

    setTimeout(() => {
      if (this.showWarningModal && this.warningCountdown <= 0) {
        this.markAbsent();
      }
    }, 20 * 60 * 1000);

    this.warningInterval = setInterval(() => {
      this.warningCountdown--;
      if (this.warningCountdown <= 0) {
        this.clearWarningTimer();
      }
    }, 1000);
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
        this.showWarningModal = false;
        this.clearWarningTimer();
        this.cdr.markForCheck();
        this.toastService.show('Sesión marcada como ausente.', 'info');
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
      error: () => {},
    }));
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
        const msg = err?.error?.error || err?.message || 'Error al ejecutar la auditoría';
        this.toastService.show(msg, 'error');
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
        this.toastService.show('Error al descargar el reporte', 'error');
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
