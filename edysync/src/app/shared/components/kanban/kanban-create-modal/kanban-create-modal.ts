import { Component, input, output, OnInit, inject, ChangeDetectorRef, ChangeDetectionStrategy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { KanbanService, KanbanTask, KanbanAssignee } from '../../../../core/services/kanban.service';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { Modal } from '../../modal/modal';
import { Button } from '../../button/button';
import { ROLE_LABELS, THERAPY_LABELS } from '../kanban-labels';

interface SelectOption<T = string | number | null> {
  value: T;
  label: string;
}

@Component({
  selector: 'app-kanban-create-modal',
  standalone: true,
  imports: [FormsModule, Modal, Button],
  templateUrl: './kanban-create-modal.html',
  styleUrl: './kanban-create-modal.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KanbanCreateModalComponent implements OnInit {
  isOpen = input(false);
  editTask = input<KanbanTask | null>(null);
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');
  /** Reasignar solo lo puede hacer el creador o un admin; si no, el selector se oculta al editar. */
  canReassign = input(true);

  close = output<void>();
  created = output<void>();
  updated = output<void>();

  title = '';
  description = '';
  therapy_type = '';
  session_id: number | null = null;
  max_minutes = 0;
  priority: 1 | 2 | 3 = 3;
  assigned_to_id: number | null = null;
  sede_id: number | null = null;
  audience = '';

  users: KanbanAssignee[] = [];
  sedes: { id: number; name: string }[] = [];
  sessions: { id: number; title: string; start: string }[] = [];
  isSaving = false;
  submitted = false;

  readonly therapyOptions = Object.entries(THERAPY_LABELS).map(([value, label]) => ({ value, label }));
  readonly priorities: SelectOption<1 | 2 | 3>[] = [
    { value: 1, label: 'Alta' },
    { value: 2, label: 'Media' },
    { value: 3, label: 'Baja' },
  ];

  private kanbanService = inject(KanbanService);
  private adminService = inject(AdminService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  ngOnInit() {
    this.loadDropdowns();
    const t = this.editTask();
    if (t) this.populateForm(t);
  }

  get isEdit(): boolean {
    return !!this.editTask();
  }

  get titleInvalid(): boolean {
    return this.submitted && !this.title.trim();
  }

  get audienceOptions(): SelectOption<string>[] {
    if (this.viewMode() === 'admin') {
      return [
        { value: '', label: 'Un usuario concreto' },
        { value: 'terapista', label: 'Todos los terapeutas' },
        { value: 'jugador', label: 'Todos los pacientes' },
        { value: 'admin', label: 'Todos los administradores' },
        { value: 'all', label: 'Todos los usuarios' },
      ];
    }
    return [
      { value: '', label: 'Un paciente concreto' },
      { value: 'my_patients', label: 'Todos mis pacientes' },
    ];
  }

  get assigneeEmptyLabel(): string {
    return 'Tarea personal (para mí)';
  }

  roleLabel(role: string): string {
    return ROLE_LABELS[role] || role;
  }

  private loadDropdowns() {
    this.kanbanService.getAssignees().subscribe({
      next: (res) => { this.users = res.users || []; this.cdr.markForCheck(); },
      error: () => { this.users = []; },
    });
    // Sedes y sesiones son ayuda opcional: si el rol no puede leerlas, el campo no se muestra y el resto funciona.
    this.adminService.getActiveSedes().subscribe({
      next: (s) => { this.sedes = s; this.cdr.markForCheck(); },
      error: () => { this.sedes = []; },
    });
    this.adminService.getSessions().subscribe({
      next: (list) => {
        this.sessions = (list || []).map((e) => ({ id: e.id, title: e.title, start: e.start })).slice(0, 200);
        this.cdr.markForCheck();
      },
      error: () => { this.sessions = []; },
    });
  }

  sessionLabel(s: { id: number; title: string; start: string }): string {
    const d = s.start ? new Date(s.start) : null;
    const when = d && !isNaN(d.getTime()) ? d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short' }) : '';
    return [s.title || `Sesión #${s.id}`, when].filter(Boolean).join(' · ');
  }

  private populateForm(task: KanbanTask) {
    this.title = task.title;
    this.description = task.description || '';
    this.therapy_type = task.therapy_type || '';
    this.session_id = task.session_id;
    this.max_minutes = task.max_minutes;
    this.priority = task.priority;
    this.assigned_to_id = task.assigned_to_id;
    this.sede_id = task.sede_id;
  }

  onClose() {
    this.close.emit();
  }

  onSubmit() {
    this.submitted = true;
    if (!this.title.trim() || this.isSaving) return;

    this.isSaving = true;
    const editing = this.editTask();
    const data: Partial<KanbanTask> & { audience?: string } = {
      title: this.title.trim(),
      description: this.description,
      therapy_type: this.therapy_type || (undefined as unknown as string),
      session_id: this.session_id,
      max_minutes: Math.max(0, Number(this.max_minutes) || 0),
      priority: this.priority,
      sede_id: this.sede_id,
    };
    if (!editing) {
      data.assigned_to_id = this.assigned_to_id;
      if (this.audience) data.audience = this.audience;
    } else if (this.assigned_to_id !== editing.assigned_to_id) {
      data.assigned_to_id = this.assigned_to_id;
    }

    const request = editing ? this.kanbanService.updateTask(editing.id, data) : this.kanbanService.createTask(data);
    request.subscribe({
      next: (res) => {
        this.isSaving = false;
        if (editing) {
          this.toast.show('Tarea actualizada', 'success');
          this.updated.emit();
        } else {
          const n = (res as { created?: number }).created;
          this.toast.show(n ? `Tarea creada para ${n} usuario${n > 1 ? 's' : ''}` : 'Tarea creada', 'success');
          this.created.emit();
        }
        this.onClose();
      },
      error: (err) => {
        this.isSaving = false;
        this.toast.show(err?.error?.message || 'No se pudo guardar la tarea.', 'error');
        this.cdr.markForCheck();
      },
    });
  }
}
