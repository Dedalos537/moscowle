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
