import { Component, input, output, inject, OnInit, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { KanbanService, KanbanTask, KanbanAttachment } from '../../../../core/services/kanban.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Modal } from '../../modal/modal';
import { Button } from '../../button/button';
import { COLUMN_LABELS, KanbanViewer, PRIORITY_META, ROLE_LABELS, canManageTask, formatBytes, formatShortDate, therapyLabel } from '../kanban-labels';

const MAX_BYTES = 20 * 1024 * 1024;

@Component({
  selector: 'app-kanban-detail-modal',
  standalone: true,
  imports: [Modal, Button],
  templateUrl: './kanban-detail-modal.html',
  styleUrl: './kanban-detail-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KanbanDetailModalComponent implements OnInit {
  task = input.required<KanbanTask>();
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');
  viewer = input<KanbanViewer | null>(null);

  close = output<void>();
  edit = output<KanbanTask>();
  changed = output<void>();

  attachments: KanbanAttachment[] = [];
  loadingAttachments = true;
  uploading = false;
  readonly formatBytes = formatBytes;
  readonly columns = Object.entries(COLUMN_LABELS).map(([value, label]) => ({ value, label }));

  private kanbanService = inject(KanbanService);
  private confirmService = inject(ConfirmService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  ngOnInit() {
    this.loadAttachments();
  }

  get canWrite(): boolean {
    return this.viewMode() !== 'patient';
  }

  get canManage(): boolean {
    return canManageTask(this.task(), this.viewer());
  }

  get priority() {
    return PRIORITY_META[this.task().priority] ?? PRIORITY_META[3];
  }

  get therapy(): string {
    return therapyLabel(this.task().therapy_type);
  }

  columnLabel(): string {
    return COLUMN_LABELS[this.task().column];
  }

  roleOf(): string {
    return ROLE_LABELS[this.viewer()?.role ?? ''] || '';
  }

  when(iso: string | null): string {
    return formatShortDate(iso);
  }

  private loadAttachments() {
    this.loadingAttachments = true;
    this.kanbanService.getAttachments(this.task().id).subscribe({
      next: (list) => { this.attachments = list; this.loadingAttachments = false; this.cdr.markForCheck(); },
      error: () => { this.attachments = []; this.loadingAttachments = false; this.cdr.markForCheck(); },
    });
  }

  onColumnChange(column: string) {
    this.kanbanService.updateTask(this.task().id, { column: column as KanbanTask['column'] }).subscribe({
      next: () => { this.toast.show('Tarea movida a ' + COLUMN_LABELS[column as KanbanTask['column']], 'success'); this.changed.emit(); this.close.emit(); },
      error: () => this.toast.show('No se pudo mover la tarea.', 'error'),
    });
  }

  onFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    if (file.size > MAX_BYTES) {
      this.toast.show('El archivo supera el máximo de 20 MB.', 'error');
      return;
    }
    this.uploading = true;
    this.kanbanService.uploadAttachment(this.task().id, file).subscribe({
      next: () => { this.uploading = false; this.toast.show('Archivo adjuntado', 'success'); this.loadAttachments(); this.changed.emit(); },
      error: (err) => { this.uploading = false; this.toast.show(err?.error?.message || 'No se pudo subir el archivo.', 'error'); this.cdr.markForCheck(); },
    });
  }

  download(att: KanbanAttachment) {
    this.kanbanService.getAttachmentData(att.id).subscribe({
      next: (full) => {
        if (!full.data) { this.toast.show('El adjunto no tiene contenido.', 'error'); return; }
        const a = document.createElement('a');
        a.href = full.data;
        a.download = att.filename;
        a.click();
      },
      error: () => this.toast.show('No se pudo descargar el adjunto.', 'error'),
    });
  }

  removeAttachment(att: KanbanAttachment) {
    this.confirmService
      .confirm({ title: 'Quitar adjunto', message: `Se eliminará "${att.filename}".`, confirmText: 'Eliminar' })
      .subscribe((ok) => {
        if (!ok) return;
        this.kanbanService.deleteAttachment(this.task().id, att.id).subscribe({
          next: () => { this.loadAttachments(); this.changed.emit(); },
          error: () => this.toast.show('No se pudo eliminar el adjunto.', 'error'),
        });
      });
  }
}
