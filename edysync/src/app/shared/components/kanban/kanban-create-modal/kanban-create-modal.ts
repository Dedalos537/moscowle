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
import { KanbanService, KanbanTask } from '../../../../core/services/kanban.service';
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

  users: any[] = [];
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
    this.adminService.getUsers().subscribe(res => this.users = res.users || []);
    this.adminService.getActiveSedes().subscribe(s => this.sedes = s);
    this.adminService.getSessions().subscribe(s => this.sessions = s);
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
