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

export interface Contract {
  id: number;
  patient_id: number;
  patient_name: string;
  patient_email?: string;
  patient_dni?: string;
  guardian_name?: string;
  guardian_dni?: string;
  guardian_contact?: string;
  name: string;
  total_amount: number;
  installment_count: number;
  installment_amount: number;
  paid_count: number;
  overdue_count: number;
  status: string;
  billing_type: string;
  currency: string;
  start_date?: string;
  end_date?: string;
  notes?: string;
  pending_amount: number;
  implementation_cost: number;
  billing_rule: string;
  cancelled_at?: string;
  refund_status?: string;
  total_refunded: number;
}

export interface ContractDetail extends Contract {
  bonus_months: number;
  sign_date?: string;
  service_start_date?: string;
  cancellation_reason?: string;
  cancellation_comment?: string;
  payment_plan?: string;
  installments: Installment[];
}

export interface Installment {
  id: number;
  number: number;
  due_date: string;
  amount: number;
  paid_amount: number;
  paid_date?: string;
  status: string;
  payment_method?: string;
  payment_id?: number;
  payment_notes?: string;
  is_free_month: boolean;
  is_implementation: boolean;
  description?: string;
  reminder_sent: boolean;
  real_amount?: number;
  refunded_amount: number;
}

export interface ContractFilter {
  search: string;
  status: string;
  month: number | null;
  year: number | null;
  sede_id: number | null;
}

export interface CreateContractForm {
  patient_id: number | null;
  total_amount: number;
  billing_type: string;
  currency: string;
  installment_count: number;
  start_date: string;
  implementation_cost: number;
  billing_rule: string;
  bonus_months: number;
  name: string;
  notes: string;
  guardian_name?: string;
  guardian_dni?: string;
  patient_dni?: string;
}

export interface PayInstallmentForm {
  installment_id: number | null;
  contract_id: number | null;
  contract_name: string;
  patient_name: string;
  installment_number: number;
  due_date: string;
  amount: number;
  method: string;
  payment_date: string;
  reference: string;
  payment_notes: string;
  is_free_month: boolean;
}

export interface CancelContractForm {
  contract_id: number | null;
  contract_name: string;
  patient_name: string;
  cancellation_date: string;
  reason: string;
  comment: string;
  disposition: string;
}
