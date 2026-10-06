import {
  Component,
  input,
  output,
  OnInit,
  inject,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { KanbanService, KanbanTask, KanbanAssignee } from '../../../../core/services/kanban.service';
import { AdminService } from '../../../../core/services/admin.service';

@Component({
  selector: 'app-kanban-create-modal',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './kanban-create-modal.html',
  styleUrl: './kanban-create-modal.scss',
})
export class KanbanCreateModalComponent implements OnInit {
  isOpen = input(false);
  editTask = input<KanbanTask | null>(null);
  viewMode = input<'admin' | 'therapist' | 'patient'>('admin');

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

  users: KanbanAssignee[] = [];
  audience = '';
  sedes: any[] = [];
  sessions: any[] = [];
  isSaving = false;

  private kanbanService = inject(KanbanService);
  private adminService = inject(AdminService);
  private cdr = inject(ChangeDetectorRef);

  ngOnInit() {
    this.loadDropdowns();
    if (this.editTask()) {
      this.populateForm(this.editTask()!);
    }
  }

  ngOnChanges() {
    if (this.editTask()) {
      this.populateForm(this.editTask()!);
    } else {
      this.resetForm();
    }
  }

  private loadDropdowns() {
    this.kanbanService.getAssignees().subscribe({
      next: (res) => { this.users = res.users || []; this.cdr.markForCheck(); },
      error: () => { this.users = []; },
    });
    // Sedes y sesiones son ayuda opcional: si el rol no puede leerlas, el formulario sigue funcionando.
    this.adminService.getActiveSedes().subscribe({ next: (s) => { this.sedes = s; this.cdr.markForCheck(); }, error: () => {} });
    this.adminService.getSessions().subscribe({ next: (s) => { this.sessions = s; this.cdr.markForCheck(); }, error: () => {} });
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

  private resetForm() {
    this.title = '';
    this.description = '';
    this.therapy_type = '';
    this.session_id = null;
    this.max_minutes = 0;
    this.priority = 3;
    this.assigned_to_id = null;
    this.sede_id = null;
    this.audience = '';
  }

  get audienceOptions(): { value: string; label: string }[] {
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

  roleLabel(role: string): string {
    const labels: Record<string, string> = { terapista: 'Terapeuta', terapeuta: 'Terapeuta', jugador: 'Paciente', admin: 'Admin', supervisor: 'Supervisor' };
    return labels[role] || role;
  }

  onClose() {
    this.close.emit();
  }

  onBackdropClick(event: MouseEvent) {
    if ((event.target as HTMLElement).classList.contains('modal-overlay')) {
      this.onClose();
    }
  }

  onSubmit() {
    if (!this.title.trim()) return;

    this.isSaving = true;
    const data: Partial<KanbanTask> = {
      title: this.title.trim(),
      description: this.description,
      therapy_type: this.therapy_type || undefined as any,
      session_id: this.session_id,
      max_minutes: this.max_minutes,
      priority: this.priority,
      assigned_to_id: this.assigned_to_id,
      sede_id: this.sede_id,
      ...(this.audience && !this.editTask() ? { audience: this.audience } : {}),
    };

    const obs = this.editTask()
      ? this.kanbanService.updateTask(this.editTask()!.id, data)
      : this.kanbanService.createTask(data);

    obs.subscribe({
      next: () => {
        this.isSaving = false;
        if (this.editTask()) {
          this.updated.emit();
        } else {
          this.created.emit();
        }
        this.onClose();
      },
      error: () => {
        this.isSaving = false;
        this.cdr.markForCheck();
      },
    });
  }
}
