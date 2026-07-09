import { Component, input } from '@angular/core';

export interface UsersStats {
  total: number;
  active: number;
  inactive: number;
  patients: number;
  therapists: number;
  supervisors: number;
  admins: number;
  retired: number;
  debtors: number;
}

type CardVariant = 'default' | 'primary' | 'secondary' | 'info' | 'warning' | 'error' | 'accent' | 'muted';

interface CardDef {
  key: keyof UsersStats;
  label: string;
  variant: CardVariant;
}

const CARDS: CardDef[] = [
  { key: 'total', label: 'Total', variant: 'default' },
  { key: 'active', label: 'Activos', variant: 'primary' },
  { key: 'inactive', label: 'Inactivos', variant: 'default' },
  { key: 'patients', label: 'Pacientes', variant: 'secondary' },
  { key: 'therapists', label: 'Terapeutas', variant: 'info' },
  { key: 'debtors', label: 'Deudores', variant: 'error' },
  { key: 'retired', label: 'Retirados', variant: 'muted' },
  { key: 'admins', label: 'Admins', variant: 'warning' },
  { key: 'supervisors', label: 'Supervisores', variant: 'accent' },
];

@Component({
  selector: 'app-users-stats-cards',
  standalone: true,
  templateUrl: './users-stats-cards.html',
  styleUrl: './users-stats-cards.scss',
})
export class UsersStatsCards {
  stats = input.required<UsersStats>();
  readonly cards = CARDS;
}
