export interface PatientRow {
  id: number;
  username: string;
  email: string;
  phone?: string;
  sede_name: string;
  therapist_name: string;
  plan_name: string;
  plan_frequency: string;
  payment_amount: number;
  sessions_total: number;
  sessions_attended: number;
  sessions_remaining: number;
  next_due_date?: string;
  status: string;
  has_plan_config: boolean;
}

export interface PaymentHistoryRow {
  id: number;
  patient_id: number;
  patient_name: string;
  amount: number;
  discount: number;
  method: string;
  reference?: string;
  date: string;
  status: string;
  receipt_image_path?: string;
  document_number?: string;
  guardian_name?: string;
  guardian_dni?: string;
}

export interface Therapist {
  id: number;
  username: string;
  email: string;
  role: string;
}

export interface RegisterForm {
  patient_id: number | null;
  amount: number;
  method: string;
  reference: string;
  next_due_date: string;
  payment_date: string;
  discount: number;
  document_number: string;
  guardian_name: string;
  guardian_dni: string;
  receipt: File | null;
}

export interface SettingsForm {
  patient_id: number | null;
  patient_name: string;
  payment_plan: string;
  payment_amount: number;
  payment_due_date: string;
}

export interface ExpenseForm {
  category: string;
  therapist_id: number | null;
  therapist_name: string;
  amount: number;
  method: string;
  date: string;
  description: string;
  receipt: File | null;
}

export interface MonthCell {
  monthKey: string;
  label: string;
  year: number;
  month: number;
  payment: PaymentHistoryRow | null;
  status: 'paid' | 'missing' | 'future' | 'na';
}
