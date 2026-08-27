import {
  Component,
  input,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  inject,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DragDropModule, CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';
import { KanbanTaskCardComponent } from '../kanban-task-card/kanban-task-card';
import { KanbanCreateModalComponent } from '../kanban-create-modal/kanban-create-modal';
import { KanbanService, KanbanTask } from '../../../../core/services/kanban.service';

export interface KanbanColumn {
  id: string;
  title: string;
  color: string;
  tasks: KanbanTask[];
}

@Component({
  selector: 'app-kanban-board',
  standalone: true,
  imports: [
    CommonModule,
    DragDropModule,
    KanbanTaskCardComponent,
    KanbanCreateModalComponent,
  ],
  templateUrl: './kanban-board.html',
  styleUrl: './kanban-board.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KanbanBoardComponent implements OnInit, OnDestroy {
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');

  columns: KanbanColumn[] = [
    { id: 'todo', title: 'Por hacer', color: '#6366f1', tasks: [] },
    { id: 'in-progress', title: 'En progreso', color: '#f59e0b', tasks: [] },
    { id: 'review', title: 'Revisión', color: '#8b5cf6', tasks: [] },
    { id: 'done', title: 'Hecho', color: '#10b981', tasks: [] },
  ];

  showCreateModal = false;
  selectedTaskDetail: KanbanTask | null = null;
  showDetailModal = false;
  isLoading = false;

  private kanbanService = inject(KanbanService);
  private cdr = inject(ChangeDetectorRef);
  private pollingInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit() {
    this.loadTasks();
    this.startPolling();
  }

  ngOnDestroy() {
    this.stopPolling();
  }

  loadTasks() {
    this.isLoading = true;
    this.kanbanService.getTasks().subscribe({
      next: (tasks) => {
        tasks.sort((a, b) => a.position - b.position);
        this.columns.forEach((col) => {
          col.tasks = tasks.filter((t) => t.column === col.id);
        });
        this.isLoading = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading = false;
        this.cdr.markForCheck();
      },
    });
  }

  onDrop(event: CdkDragDrop<KanbanTask[]>) {
    if (event.previousContainer === event.container) {
      const tasks = event.container.data;
      moveItemInArray(tasks, event.previousIndex, event.currentIndex);
      tasks.forEach((t, i) => (t.position = i));
      tasks.forEach((t) =>
        this.kanbanService.updateTask(t.id, { position: t.position }).subscribe()
      );
    } else {
      const task = event.previousContainer.data[event.previousIndex];
      event.previousContainer.data.splice(event.previousIndex, 1);
      event.container.data.splice(event.currentIndex, 0, task);
      task.column = event.container.id as KanbanTask['column'];
      event.container.data.forEach((t, i) => (t.position = i));
      this.kanbanService
        .updateTask(task.id, { column: task.column, position: task.position })
        .subscribe();
    }
    this.cdr.markForCheck();
  }

  onTaskMoved() {
    this.loadTasks();
  }

  onTaskExtended() {
    this.loadTasks();
  }

  onTaskDeleted() {
    this.loadTasks();
  }

  onTaskEdited() {
    this.loadTasks();
  }

  openTaskDetail(task: KanbanTask) {
    this.selectedTaskDetail = task;
    this.showDetailModal = true;
    this.cdr.markForCheck();
  }

  closeTaskDetail() {
    this.selectedTaskDetail = null;
    this.showDetailModal = false;
    this.cdr.markForCheck();
  }

  openCreateModal() {
    this.showCreateModal = true;
    this.cdr.markForCheck();
  }

  closeCreateModal() {
    this.showCreateModal = false;
    this.cdr.markForCheck();
  }

  onTaskCreated() {
    this.showCreateModal = false;
    this.loadTasks();
  }

  getConnectedLists(excludeId: string): string[] {
    return this.columns.filter((c) => c.id !== excludeId).map((c) => c.id);
  }

  getColumnTasks(columnId: string): KanbanTask[] {
    const col = this.columns.find((c) => c.id === columnId);
    return col ? col.tasks : [];
  }

  private startPolling() {
    this.pollingInterval = setInterval(() => this.loadTasks(), 10_000);
  }

  private stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }
}
