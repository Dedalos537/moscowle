/** Libro de cobranza (PRP 008): cronograma del paciente e importación desde Excel. */

export interface ScheduleInstallment {
  id: number;
  number: number;
  due_date: string;
  amount: number;
  paid: number;
  remaining: number;
  status: 'pending' | 'partial' | 'paid' | 'free' | 'cancelled';
  overdue: boolean;
  payments: { payment_id: number; amount: number; date: string | null; method: string }[];
}

export interface ScheduleContract {
  id: number;
  name: string;
  status: string;
  renewable: boolean;
  billing_type: string;
  payment_day: number | null;
  installments: ScheduleInstallment[];
}

export interface PatientSchedule {
  success: boolean;
  contracts: ScheduleContract[];
  credit: number;
  other_payments: { id: number; date: string | null; amount: number; method: string; kind: 'one_off' | 'unassigned'; category: string | null }[];
}

export interface BillingImportRow {
  sheet: 'Pagos' | 'Contratos';
  row: number;
  status: 'ok' | 'skip' | 'error' | 'warn' | 'info';
  message: string;
}

export interface BillingImportResult {
  success: boolean;
  ok: boolean;
  applied: boolean;
  import_id?: number;
  sha256: string;
  summary: Record<string, number>;
  rows: BillingImportRow[];
  message?: string;
}

export interface BillingImportRecord {
  id: number;
  file_name: string;
  created_at: string;
  summary: Record<string, number>;
  allocations: number;
}
