import { Pipe, PipeTransform } from '@angular/core';

const STATUS: Record<string, string> = {
  scheduled: 'Programada',
  in_progress: 'En curso',
  completed: 'Realizada',
  cancelled: 'Cancelada',
  canceled: 'Cancelada',
  no_show: 'No asistió',
  rescheduled: 'Reprogramada',
};
const ATTENDANCE: Record<string, string> = { present: 'Asistió', absent: 'Faltó', pending: 'Sin registrar' };

/** Estado o asistencia de una sesión en español: `{{ s.status | sessionLabel }}`, `{{ s.attendance | sessionLabel: 'attendance' }}`. */
@Pipe({ name: 'sessionLabel', standalone: true })
export class SessionLabelPipe implements PipeTransform {
  transform(value: string | null | undefined, kind: 'status' | 'attendance' = 'status'): string {
    if (!value) return kind === 'attendance' ? 'Sin registrar' : '—';
    const map = kind === 'attendance' ? ATTENDANCE : STATUS;
    return map[value] ?? value;
  }
}
