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
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { KanbanService, KanbanTask } from '../../../../core/services/kanban.service';

type Urgency = 'normal' | 'warning' | 'expired';

@Component({
  selector: 'app-kanban-task-card',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './kanban-task-card.html',
  styleUrl: './kanban-task-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KanbanTaskCardComponent implements OnInit, OnDestroy {
  task = input.required<KanbanTask>();
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');

  taskClicked = output<KanbanTask>();
  taskMoved = output<void>();
  taskDeleted = output<void>();
  taskEdited = output<void>();

  countdown = '';
  urgency: Urgency = 'normal';

  private kanbanService = inject(KanbanService);
  private cdr = inject(ChangeDetectorRef);
  private timerInterval: ReturnType<typeof setInterval> | null = null;

  private allColumns: KanbanTask['column'][] = ['todo', 'in-progress', 'review', 'done'];

  otherColumns = computed<KanbanTask['column'][]>(() =>
    this.allColumns.filter((c) => c !== this.task().column)
  );

  columnLabels: Record<string, string> = {
    'todo': 'Por hacer',
    'in-progress': 'En progreso',
    'review': 'Revisión',
    'done': 'Hecho',
  };

  ngOnInit() {
    this.updateTimer();
    if (this.task().timer_start) {
      this.timerInterval = setInterval(() => this.updateTimer(), 1000);
    }
  }

  ngOnDestroy() {
    this.clearTimer();
  }

  private clearTimer() {
    if (this.timerInterval) {
      clearInterval(this.timerInterval);
      this.timerInterval = null;
    }
  }

  private updateTimer() {
    const t = this.task();
    if (!t.timer_start) {
      this.countdown = '';
      this.urgency = 'normal';
      return;
    }

    const start = new Date(t.timer_start).getTime();
    const elapsed = Date.now() - start;
    const totalMs = t.max_minutes * 60 * 1000;
    const remaining = totalMs - elapsed;

    if (remaining <= 0) {
      this.countdown = '00:00';
      this.urgency = 'expired';
    } else {
      if (remaining < 5 * 60 * 1000) {
        this.urgency = 'warning';
      } else {
        this.urgency = 'normal';
      }
      this.countdown = this.formatTime(remaining);
    }
    this.cdr.markForCheck();
  }

  private formatTime(ms: number): string {
    const totalSeconds = Math.floor(ms / 1000);
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;

    const pad = (n: number) => n.toString().padStart(2, '0');

    if (days > 0) {
      return `${days}d ${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }
    if (hours > 0) {
      return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
    }
    return `${pad(minutes)}:${pad(seconds)}`;
  }

  get priorityLabel(): string {
    switch (this.task().priority) {
      case 1: return 'Alta';
      case 2: return 'Media';
      case 3: return 'Baja';
      default: return '';
    }
  }

  get priorityClass(): string {
    switch (this.task().priority) {
      case 1: return 'bg-red-500';
      case 2: return 'bg-amber-500';
      case 3: return 'bg-green-500';
      default: return 'bg-gray-400';
    }
  }

  get canDelete(): boolean {
    return this.viewMode() !== 'patient';
  }

  get showExtendButtons(): boolean {
    return this.task().column === 'in-progress';
  }

  onCardClick() {
    this.taskClicked.emit(this.task());
  }

  onMoveToColumn(column: KanbanTask['column']) {
    this.kanbanService
      .updateTask(this.task().id, { column })
      .subscribe(() => this.taskMoved.emit());
  }

  onExtend(minutes: number) {
    this.kanbanService
      .extendTimer(this.task().id, minutes)
      .subscribe(() => {
        this.taskEdited.emit();
      });
  }

  onDelete(event: MouseEvent) {
    event.stopPropagation();
    this.kanbanService
      .deleteTask(this.task().id)
      .subscribe(() => this.taskDeleted.emit());
  }

  trackByColumn(_index: number, column: string): string {
    return column;
  }
}
