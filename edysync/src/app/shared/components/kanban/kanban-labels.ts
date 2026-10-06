import { KanbanTask } from '../../../core/services/kanban.service';

export const THERAPY_LABELS: Record<string, string> = {
  terapia_lenguaje: 'Terapia de Lenguaje',
  terapia_ocupacional: 'Terapia Ocupacional',
  psicologia: 'Psicología',
  neuropsicologia: 'Neuropsicología',
  fisioterapia: 'Fisioterapia',
};

export const ROLE_LABELS: Record<string, string> = {
  terapista: 'Terapeuta',
  terapeuta: 'Terapeuta',
  jugador: 'Paciente',
  admin: 'Admin',
  supervisor: 'Supervisor',
};

export const COLUMN_LABELS: Record<KanbanTask['column'], string> = {
  'todo': 'Por hacer',
  'in-progress': 'En progreso',
  'review': 'Revisión',
  'done': 'Hecho',
};

export const PRIORITY_META: Record<number, { label: string; badge: string }> = {
  1: { label: 'Alta', badge: 'badge--error' },
  2: { label: 'Media', badge: 'badge--warning' },
  3: { label: 'Baja', badge: 'badge--success' },
};

export interface KanbanViewer {
  id: number;
  role: string;
}

export function therapyLabel(key: string | null | undefined): string {
  return key ? THERAPY_LABELS[key] || key : '';
}

/** Admin/supervisor, o quien creó la tarea, puede borrarla o reasignarla (misma regla que el backend). */
export function canManageTask(task: KanbanTask, viewer: KanbanViewer | null): boolean {
  if (!viewer) return false;
  return viewer.role === 'admin' || viewer.role === 'supervisor' || task.created_by_id === viewer.id;
}

export function formatShortDate(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso.endsWith('Z') ? iso : iso + 'Z');
  return isNaN(d.getTime()) ? '' : d.toLocaleDateString('es-PE', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}
