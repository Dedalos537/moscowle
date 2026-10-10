export interface Sede {
  id: number;
  name: string;
  address: string;
  active: boolean;
  created_at: string;
  stats?: SedeStats;
}

export interface SedeStats {
  patients: { total: number; active?: number };
  sessions: { total_completed: number; total_scheduled?: number; pending?: number; this_month?: number; total?: number };
  payments: { total_revenue: number; pending?: number; this_month?: number; transactions?: number };
  therapists?: { count?: number; names?: string[] };
}

export interface SedeAnalytics {
  sede: Sede;
  patient_count: number;
  revenue: number;
  session_count: number;
  therapists: string[];
}

// ── Balanced Scorecard (GET /api/admin/sedes/scorecard) ──────────────────────
export type ScorecardPeriod = 'month' | 'quarter' | 'year';
export type KpiUnit = 'money' | 'pct' | 'int' | 'dec';
export type KpiStatus = 'good' | 'warn' | 'bad' | 'none';
export type PerspectiveKey = 'financial' | 'patients' | 'process' | 'growth';

export interface ScorecardKpi {
  key: string;
  perspective: PerspectiveKey;
  label: string;
  unit: KpiUnit;
  direction: 'up' | 'down';
  value: number | null;
  previous: number | null;
  target: number | null;
  status: KpiStatus;
  trend: (number | null)[];
  how: string;
}

export interface ScorecardPerspective {
  key: PerspectiveKey;
  label: string;
  question: string;
  score?: number | null;
}

export interface SedeScore {
  id: number;
  name: string;
  address: string | null;
  score: number | null;
  perspectives: ScorecardPerspective[];
  kpis: ScorecardKpi[];
  counts: Record<string, number>;
}

export interface Scorecard {
  success: boolean;
  period: ScorecardPeriod;
  period_label: string;
  range: { from: string; to: string };
  previous_range: { from: string; to: string };
  months: string[];
  perspectives: ScorecardPerspective[];
  targets: Record<string, number | null>;
  sedes: SedeScore[];
}
