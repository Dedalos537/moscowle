import { ScorecardKpi, ScorecardPeriod, ScorecardPerspective } from './sede';

export interface PersonRef {
  id: number;
  name: string;
  code?: string;
}

export interface FlowMonth {
  month: string;
  new: number;
  left: number;
  net: number;
}

export interface TodaySession {
  id: number;
  start: string;
  status: string;
  attendance: string | null;
  patient: PersonRef;
  therapist: PersonRef;
}

export interface DuePayment {
  patient: PersonRef;
  amount: number;
  phone: string | null;
}

export type RiskKind = 'debt' | 'absences' | 'idle' | 'no_schedule' | 'plan_ending';

export interface RiskItem {
  patient: PersonRef & { sede_id: number | null };
  phone: string | null;
  score: number;
  reasons: { kind: RiskKind; label: string; detail: string }[];
  last_session: string | null;
  next_session: string | null;
  overdue: number;
  sessions_remaining: number | null;
}

export interface TeamRow {
  id: number;
  name: string;
  patients: number;
  sessions_done: number;
  sessions_scheduled: number;
  next_7_days: number;
  attendance: number | null;
  cancel_rate: number | null;
}

export interface SedeSummary {
  id: number;
  name: string;
  score: number | null;
  kpis: Record<'revenue' | 'active_patients' | 'attendance' | 'collection' | 'retention', Pick<ScorecardKpi, 'value' | 'previous' | 'status'>>;
}

/** GET /api/admin/dashboard: hoy, crecimiento, riesgo de abandono, equipo y sedes. */
export interface CenterDashboard {
  success: boolean;
  period: ScorecardPeriod;
  period_label: string;
  range: { from: string; to: string };
  previous_range: { from: string; to: string };
  months: string[];
  sede_id: number | null;
  score: number | null;
  perspectives: ScorecardPerspective[];
  pulse: ScorecardKpi[];
  flow: FlowMonth[];
  today: {
    sessions: { total: number; by_status: Record<string, number>; items: TodaySession[] };
    payments_due: { count: number; total: number; items: DuePayment[] };
    pending: { requests: number; password_resets: number; incidents: number };
  };
  risks: { total: number; by_kind: Partial<Record<RiskKind, number>>; items: RiskItem[] };
  team: TeamRow[];
  sedes: SedeSummary[];
  data_quality: { without_plan: number; items: PersonRef[] };
  active_patients_now: number;
}
