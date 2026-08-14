import { Component, ChangeDetectionStrategy, ChangeDetectorRef, inject, output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Modal } from '../modal/modal';
import { AdminService } from '../../../core/services/admin.service';
import { getToolLabel, getToolIcon, getParamLabel } from '../../../core/services/mcp-tool-meta';

export interface PendingAction {
  name: string;
  args: Record<string, unknown>;
  tool_call_text?: string;
}

interface ArgRow {
  key: string;
  label: string;
  value: string;
}

interface PatientOption {
  id: number;
  username: string;
  email: string;
  phone: string;
}

const ID_KEYS = ['patient_id', 'user_id', 'therapist_id'];

@Component({
  selector: 'app-chat-confirm-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Modal],
  templateUrl: './chat-confirm-dialog.html',
  styleUrl: './chat-confirm-dialog.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatConfirmDialog {
  confirmAction = output<PendingAction>();
  cancelAction = output<void>();

  private admin = inject(AdminService);
  private cdr = inject(ChangeDetectorRef);

  visible = false;
  pending: PendingAction | null = null;

  rows: ArgRow[] = [];
  editing = false;
  editedJson = '';
  jsonError: string | null = null;

  patientQuery = '';
  patientSearching = false;
  patientResults: PatientOption[] = [];
  selectedPatient: PatientOption | null = null;
  private patientSearchTimer: ReturnType<typeof setTimeout> | null = null;

  get title(): string {
    return this.pending ? `Confirmar: ${getToolLabel(this.pending.name)}` : 'Confirmar acción';
  }

  open(action: PendingAction) {
    this.pending = action;
    this.rows = this.buildRows(action.args);
    this.editing = false;
    this.jsonError = null;
    this.editedJson = JSON.stringify(action.args, null, 2);
    this.patientQuery = '';
    this.patientResults = [];
    this.selectedPatient = null;
    this.visible = true;
    this.cdr.markForCheck();
  }

  close() {
    this.visible = false;
    this.pending = null;
    if (this.patientSearchTimer) {
      clearTimeout(this.patientSearchTimer);
      this.patientSearchTimer = null;
    }
    this.cdr.markForCheck();
  }

  closeCancel() {
    this.close();
    this.cancelAction.emit();
  }

  getToolIconName(): string {
    return this.pending ? getToolIcon(this.pending.name) : 'wrench';
  }

  hasPatientId(): boolean {
    return !!this.pending && 'patient_id' in (this.pending.args || {});
  }

  private buildRows(args: Record<string, unknown>): ArgRow[] {
    const keys = Object.keys(args || {});
    const ordered = [...keys.filter((k) => ID_KEYS.includes(k)), ...keys.filter((k) => !ID_KEYS.includes(k))];
    return ordered.map((key) => {
      let value = String(args[key] ?? '');
      if (key === 'password') value = '••••••';
      return { key, label: getParamLabel(key), value };
    });
  }

  toggleEdit() {
    this.editing = !this.editing;
    this.jsonError = null;
    if (this.editing) {
      this.editedJson = JSON.stringify(this.getFinalArgs(), null, 2);
    }
    this.cdr.markForCheck();
  }

  private getFinalArgs(): Record<string, unknown> {
    if (!this.pending) return {};
    if (this.editing) {
      try {
        return JSON.parse(this.editedJson);
      } catch {
        return this.pending.args;
      }
    }
    if (this.selectedPatient && 'patient_id' in (this.pending.args || {})) {
      return { ...this.pending.args, patient_id: this.selectedPatient.id };
    }
    return { ...this.pending.args };
  }

  onPatientSearch() {
    if (this.patientSearchTimer) clearTimeout(this.patientSearchTimer);
    this.patientSearchTimer = setTimeout(() => {
      const q = this.patientQuery.trim();
      if (q.length < 2) {
        this.patientResults = [];
        this.patientSearching = false;
        this.cdr.markForCheck();
        return;
      }
      this.patientSearching = true;
      this.cdr.markForCheck();
      this.admin.searchPatients(q).subscribe({
        next: (res) => {
          this.patientResults = res.patients || [];
          this.patientSearching = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.patientResults = [];
          this.patientSearching = false;
          this.cdr.markForCheck();
        },
      });
    }, 250);
  }

  selectPatient(p: PatientOption) {
    this.selectedPatient = p;
    this.patientResults = [];
    this.patientQuery = `${p.username} #${p.id}`;
    this.cdr.markForCheck();
  }

  confirm() {
    if (!this.pending) return;
    let args = this.pending.args;
    if (this.editing) {
      try {
        args = JSON.parse(this.editedJson);
        this.jsonError = null;
      } catch {
        this.jsonError = 'El JSON no es válido. Revísalo antes de confirmar.';
        this.cdr.markForCheck();
        return;
      }
    } else if (this.selectedPatient && 'patient_id' in args) {
      args = { ...args, patient_id: this.selectedPatient.id };
    }
    const action: PendingAction = { name: this.pending.name, args, tool_call_text: this.pending.tool_call_text };
    this.visible = false;
    this.pending = null;
    this.confirmAction.emit(action);
    this.cdr.markForCheck();
  }
}
