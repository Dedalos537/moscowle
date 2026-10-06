import {
  Component,
  input,
  OnInit,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  inject,
} from '@angular/core';
import { DragDropModule, CdkDragDrop, moveItemInArray } from '@angular/cdk/drag-drop';
import { KanbanTaskCardComponent } from '../kanban-task-card/kanban-task-card';
import { KanbanCreateModalComponent } from '../kanban-create-modal/kanban-create-modal';
import { KanbanDetailModalComponent } from '../kanban-detail-modal/kanban-detail-modal';
import { AuthService } from '../../../../core/services/auth.service';
import { ToastService } from '../../../../core/services/toast.service';
import { KanbanViewer, canManageTask } from '../kanban-labels';
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
    DragDropModule,
    KanbanTaskCardComponent,
    KanbanCreateModalComponent,
    KanbanDetailModalComponent,
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
  editingTask: KanbanTask | null = null;
  showDetailModal = false;
  isLoading = false;
  loaded = false;
  lastUpdated: Date | null = null;
  loadError = false;
  dragging = false;
  viewer: KanbanViewer | null = null;

  private kanbanService = inject(KanbanService);
  private cdr = inject(ChangeDetectorRef);
  private auth = inject(AuthService);
  private toast = inject(ToastService);
  private authSub: { unsubscribe(): void } | null = null;
  private pollingInterval: ReturnType<typeof setInterval> | null = null;

  private onVisible = () => {
    if (document.visibilityState === 'visible' && !this.dragging) this.loadTasks();
  };

  ngOnInit() {
    document.addEventListener('visibilitychange', this.onVisible);
    this.authSub = this.auth.currentUser$.subscribe((u) => {
      this.viewer = u ? { id: u.id, role: u.role } : null;
      this.cdr.markForCheck();
    });
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
    document.removeEventListener('visibilitychange', this.onVisible);
    this.authSub?.unsubscribe();
    this.stopPolling();
  }

  get canWrite(): boolean {
    return this.viewMode() !== 'patient';
  }

  get totalTasks(): number {
    return this.columns.reduce((n, c) => n + c.tasks.length, 0);
  }

  get expiredCount(): number {
    return this.columns.filter((c) => c.id !== 'done').reduce((n, c) => n + c.tasks.filter((t) => t.is_expired).length, 0);
  }

  get unassignedCount(): number {
    return this.columns.reduce((n, c) => n + c.tasks.filter((t) => !t.assigned_to_id).length, 0);
  }

  get hasActiveFilters(): boolean {
    const f = this.filters;
    return !!(f.therapy_type || f.priority || f.role || f.assigned_to || f.scope === 'mine');
  }

  clearFilters() {
    this.filters = { therapy_type: '', priority: '', role: '', assigned_to: '', scope: 'all' };
    this.loadTasks();
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
        this.loaded = true;
        this.lastUpdated = new Date();
        this.loadError = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.isLoading = false;
        this.loadError = true;
        this.cdr.markForCheck();
      },
    });
  }

  onDragStarted() {
    this.dragging = true;
  }

  onDrop(event: CdkDragDrop<KanbanTask[]>) {
    this.dragging = false;
    const fail = () => {
      this.toast.show('No se pudo guardar el cambio. Se recargó el tablero.', 'error');
      this.loadTasks();
    };
    if (event.previousContainer === event.container) {
      const tasks = event.container.data;
      moveItemInArray(tasks, event.previousIndex, event.currentIndex);
      tasks.forEach((t, i) => {
        if (t.position !== i) {
          t.position = i;
          this.kanbanService.updateTask(t.id, { position: i }).subscribe({ error: fail });
        }
      });
    } else {
      const task = event.previousContainer.data[event.previousIndex];
      event.previousContainer.data.splice(event.previousIndex, 1);
      event.container.data.splice(event.currentIndex, 0, task);
      task.column = event.container.id as KanbanTask['column'];
      event.container.data.forEach((t, i) => (t.position = i));
      this.kanbanService.updateTask(task.id, { column: task.column, position: task.position }).subscribe({ next: () => this.loadTasks(), error: fail });
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

  canReassign(task: KanbanTask | null): boolean {
    return !!task && canManageTask(task, this.viewer);
  }

  openEdit(task: KanbanTask) {
    this.closeTaskDetail();
    this.editingTask = task;
    this.showCreateModal = true;
    this.cdr.markForCheck();
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
    this.editingTask = null;
    this.showCreateModal = true;
    this.cdr.markForCheck();
  }

  closeCreateModal() {
    this.showCreateModal = false;
    this.editingTask = null;
    this.cdr.markForCheck();
  }

  onTaskCreated() {
    this.showCreateModal = false;
    this.editingTask = null;
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
    // Se pausa mientras se arrastra o hay un modal abierto para no pisar lo que el usuario está haciendo.
    this.pollingInterval = setInterval(() => {
      if (document.visibilityState === 'visible' && !this.dragging && !this.showCreateModal && !this.showDetailModal) this.loadTasks();
    }, 10_000);
  }

  private stopPolling() {
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
      this.pollingInterval = null;
    }
  }
}
