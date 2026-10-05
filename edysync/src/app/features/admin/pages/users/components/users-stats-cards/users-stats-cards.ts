import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface UsersStats {
  total: number;
  active: number;
  inactive: number;
  patients: number;
  activePatients: number;
  therapists: number;
  supervisors: number;
  admins: number;
  retired: number;
  debtors: number;
  noTherapist: number;
}

export type StatKey = 'patients_active' | 'debtors' | 'no_therapist' | 'total';

type Tone = 'default' | 'primary' | 'warning' | 'error';

interface CardDef {
  key: StatKey;
  label: string;
  hint: string;
  tone: Tone;
  value: (stats: UsersStats) => number;
}

/** Lo que el staff necesita atender hoy, no un contador por cada rol. Cada tarjeta aplica su filtro al pulsarla. */
const CARDS: CardDef[] = [
  { key: 'patients_active', label: 'Pacientes activos', hint: 'En tratamiento', tone: 'primary', value: (s) => s.activePatients },
  { key: 'debtors', label: 'Deudores', hint: 'Con pagos pendientes', tone: 'error', value: (s) => s.debtors },
  { key: 'no_therapist', label: 'Sin terapeuta', hint: 'Pacientes por asignar', tone: 'warning', value: (s) => s.noTherapist },
  { key: 'total', label: 'Todos los usuarios', hint: 'Ver el directorio completo', tone: 'default', value: (s) => s.total },
];

@Component({
  selector: 'app-users-stats-cards',
  standalone: true,
  templateUrl: './users-stats-cards.html',
  styleUrl: './users-stats-cards.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UsersStatsCards {
  stats = input.required<UsersStats>();
  /** Tarjeta cuyo filtro esta aplicado ahora mismo (aria-pressed). */
  activeKey = input<StatKey | null>(null);
  selected = output<StatKey>();

  readonly cards = CARDS;
}
