import {
  Component,
  inject,
  input,
  output,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  computed,
  effect,
} from '@angular/core';
import { KanbanService, KanbanTask } from '../../../../core/services/kanban.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { ToastService } from '../../../../core/services/toast.service';
import { COLUMN_LABELS, KanbanViewer, PRIORITY_META, ROLE_LABELS, canManageTask, formatShortDate, therapyLabel } from '../kanban-labels';

type Urgency = 'normal' | 'warning' | 'expired';

@Component({
  selector: 'app-kanban-task-card',
  standalone: true,
  imports: [],
  templateUrl: './kanban-task-card.html',
  styleUrl: './kanban-task-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KanbanTaskCardComponent implements OnInit, OnDestroy {
  task = input.required<KanbanTask>();
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');
  viewer = input<KanbanViewer | null>(null);

  taskClicked = output<KanbanTask>();
  taskMoved = output<void>();
  taskDeleted = output<void>();
  taskEdited = output<void>();

  countdown = '';
  paused = false;
  private fetchedAt = Date.now();
  urgency: Urgency = 'normal';
  readonly columnLabels = COLUMN_LABELS;
  readonly roleLabels = ROLE_LABELS;

  private kanbanService = inject(KanbanService);
  private confirmService = inject(ConfirmService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);
  private timerInterval: ReturnType<typeof setInterval> | null = null;

  private allColumns: KanbanTask['column'][] = ['todo', 'in-progress', 'review', 'done'];

  otherColumns = computed<KanbanTask['column'][]>(() => this.allColumns.filter((c) => c !== this.task().column));

  constructor() {
    // Las tareas llegan reemplazadas por el sondeo: el reloj se resincroniza cada vez que cambia la tarea.
    effect(() => {
      this.task();
      this.fetchedAt = Date.now();
      this.syncTimer();
    });
  }

  ngOnInit() {
    this.syncTimer();
  }

  ngOnDestroy() {
    this.stopTick();
  }

  private stopTick() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private syncTimer() {
    this.stopTick();
    this.updateTimer();
    if (this.task().timer_running) {
      this.timerInterval = setInterval(() => this.updateTimer(), 1000);
    }
  }

  /** Marca de tiempo del servidor (UTC sin zona) → ms. */
  private serverMs(iso: string): number {
    return new Date(iso.endsWith('Z') ? iso : iso + 'Z').getTime();
  }

  private updateTimer() {
    const t = this.task();
    this.paused = false;
    if (!(t.max_minutes > 0) || t.column === 'done') {
      this.countdown = '';
      this.urgency = 'normal';
      this.cdr.markForCheck();
      return;
    }
    // elapsed_seconds ya incluye el tramo en curso al momento de la respuesta; se suma solo lo transcurrido desde entonces.
    const running = t.timer_running && t.timer_start;
    const base = t.elapsed_seconds || 0;
    const sinceFetch = running ? Math.max(0, (Date.now() - this.fetchedAt) / 1000) : 0;
    const remaining = (t.max_minutes * 60 - base - sinceFetch) * 1000;
    this.paused = !t.timer_running && t.column !== 'todo';
    if (t.column === 'todo' && base === 0) {
      this.countdown = '';
      this.urgency = 'normal';
    } else if (remaining <= 0) {
      this.countdown = '00:00';
      this.urgency = 'expired';
    } else {
      this.urgency = !this.paused && remaining < 5 * 60_000 ? 'warning' : 'normal';
      this.countdown = this.formatTime(remaining);
    }
    this.cdr.markForCheck();
  }

  private formatTime(ms: number): string {
    const s = Math.floor(ms / 1000);
    const days = Math.floor(s / 86400);
    const pad = (n: number) => n.toString().padStart(2, '0');
    const hms = `${pad(Math.floor((s % 86400) / 3600))}:${pad(Math.floor((s % 3600) / 60))}:${pad(s % 60)}`;
    return days > 0 ? `${days}d ${hms}` : hms;
  }

  get priority() {
    return PRIORITY_META[this.task().priority] ?? PRIORITY_META[3];
  }

  get therapy(): string {
    return therapyLabel(this.task().therapy_type);
  }

  get canDelete(): boolean {
    return canManageTask(this.task(), this.viewer());
  }

  /** Los pacientes solo leen su tablero: el backend rechaza cualquier escritura suya. */
  get canWrite(): boolean {
    return this.viewMode() !== 'patient';
  }

  get showExtendButtons(): boolean {
    return this.canWrite && this.task().column === 'in-progress' && this.task().max_minutes > 0;
  }

  get updatedLabel(): string {
    return formatShortDate(this.task().updated_at);
  }

  get creatorShown(): string | null {
    const t = this.task();
    return t.created_by_name && t.created_by_id !== t.assigned_to_id ? t.created_by_name : null;
  }

  onOpen() {
    this.taskClicked.emit(this.task());
  }

  onMoveToColumn(column: KanbanTask['column']) {
    this.kanbanService.updateTask(this.task().id, { column }).subscribe({
      next: () => this.taskMoved.emit(),
      error: () => this.toast.show('No se pudo mover la tarea.', 'error'),
    });
  }

  onExtend(minutes: number) {
    this.kanbanService.extendTimer(this.task().id, minutes).subscribe({
      next: () => this.taskEdited.emit(),
      error: () => this.toast.show('No se pudo extender el tiempo.', 'error'),
    });
  }

  onDelete() {
    this.confirmService
      .confirm({ title: 'Eliminar tarea', message: `Se eliminará "${this.task().title}" y sus adjuntos. No se puede deshacer.`, confirmText: 'Eliminar' })
      .subscribe((ok) => {
        if (!ok) return;
        this.kanbanService.deleteTask(this.task().id).subscribe({
          next: () => this.taskDeleted.emit(),
          error: (err) => this.toast.show(err?.error?.message || 'No se pudo eliminar la tarea.', 'error'),
        });
      });
  }
}
