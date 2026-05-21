// DCE — Diego Centeno Estuvo Acá
export interface DashboardOverview {
  therapists: number;
  patients: number;
  sessions_total: number;
  avg_accuracy: number;
}

export interface SmartAction {
  id: number;
  module: string;
  description: string;
  automation_level: 'manual' | 'requires_confirmation' | 'auto';
  status: 'pending' | 'resolved' | 'ignored';
  suggested_payload?: any;
  created_at: string;
}

export interface FinancialSummary {
  income_real: number;
  income_expected: number;
  overdue_amount: number;
  overdue_users_count: number;
  expenses?: number;
  net_profit?: number;
}

export interface SedeStatsEntry {
  id: number;
  name: string;
  count: number;
}
