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
import { KanbanService, KanbanTask, KanbanAssignee, KanbanFilters } from '../../../../core/services/kanban.service';

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

  // Filtros. Los de usuario solo se muestran a admin/supervisor; para el resto el backend ya devuelve solo lo suyo.
  filters = { therapy_type: '', priority: '', role: '', assigned_to: '', scope: 'all' as 'all' | 'mine' };
  assignees: KanbanAssignee[] = [];

  readonly roleOptions = [
    { value: '', label: 'Todos los tipos de usuario' },
    { value: 'terapista', label: 'Terapeutas' },
    { value: 'jugador', label: 'Pacientes' },
    { value: 'admin', label: 'Administradores' },
    { value: 'supervisor', label: 'Supervisores' },
  ];

  showCreateModal = false;
  selectedTaskDetail: KanbanTask | null = null;
  showDetailModal = false;
  isLoading = false;

  private kanbanService = inject(KanbanService);
  private cdr = inject(ChangeDetectorRef);
  private pollingInterval: ReturnType<typeof setInterval> | null = null;

  ngOnInit() {
    if (this.viewMode() === 'admin') this.loadAssignees();
    this.loadTasks();
    this.startPolling();
  }

  get isAdminView(): boolean {
    return this.viewMode() === 'admin';
  }

  /** Usuarios del selector, acotados al tipo de usuario elegido. */
  get filteredAssignees(): KanbanAssignee[] {
    const r = this.filters.role;
    if (!r) return this.assignees;
    return this.assignees.filter((u) => u.role === r || (r === 'terapista' && u.role === 'terapeuta'));
  }

  private loadAssignees() {
    this.kanbanService.getAssignees().subscribe({
      next: (res) => { this.assignees = res.users || []; this.cdr.markForCheck(); },
      error: () => { this.assignees = []; },
    });
  }

  onFilterChange(key: 'therapy_type' | 'priority' | 'role' | 'assigned_to', value: string) {
    this.filters[key] = value;
    // Elegir un tipo de usuario descarta un usuario que ya no pertenezca a él.
    if (key === 'role' && this.filters.assigned_to && !this.filteredAssignees.some((u) => String(u.id) === this.filters.assigned_to)) {
      this.filters.assigned_to = '';
    }
    this.loadTasks();
  }

  setScope(scope: 'all' | 'mine') {
    this.filters.scope = scope;
    this.loadTasks();
  }

  private buildFilters(): KanbanFilters {
    const f = this.filters;
    const out: KanbanFilters = {};
    if (f.therapy_type) out.therapy_type = f.therapy_type;
    if (f.priority) out.priority = f.priority;
    if (this.isAdminView) {
      if (f.scope === 'mine') out.mine = true;
      else if (f.assigned_to) out.assigned_to = f.assigned_to === 'unassigned' ? 'unassigned' : Number(f.assigned_to);
      else if (f.role) out.role = f.role;
    }
    return out;
  }

  ngOnDestroy() {
    this.stopPolling();
  }

  loadTasks() {
    this.isLoading = true;
    this.kanbanService.getTasks(this.buildFilters()).subscribe({
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
