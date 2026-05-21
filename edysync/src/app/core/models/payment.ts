// DCE — Diego Centeno Estuvo Acá
export interface Payment {
  id: number;
  patient_id: number;
  patient?: { id: number; username: string };
  amount: number;
  discount: number;
  method: string;
  reference?: string;
  receipt_image_path?: string;
  status: string;
  notes?: string;
  date: string;
  created_at?: string;
}

export interface PatientPaymentStatus {
  id: number;
  username: string;
  email: string;
  sede_name?: string;
  payment_amount: number;
  sessions_total: number;
  sessions_attended: number;
  sessions_remaining: number;
  next_due_date?: string;
  modality?: string;
  status: string;
  phone?: string;
  guardian_name?: string;
}

export interface PaymentFormData {
  patient_id: number;
  amount: number;
  discount?: number;
  method: string;
  reference?: string;
  next_due_date?: string;
  payment_date?: string;
  receipt?: File;
  document_number?: string;
  guardian_name?: string;
}

export interface DebtReport {
  por_sede: Record<string, DebtSedeGroup>;
  total_deuda: number;
  total_pacientes: number;
}

export interface DebtSedeGroup {
  sede_name: string;
  sede_id: number;
  deudores: DebtorItem[];
  total_deuda: number;
}

export interface DebtorItem {
  paciente: string;
  username?: string;
  email?: string;
  phone?: string;
  monto: number;
  modality?: string;
  fecha_vencimiento?: string;
  payment_day?: number;
  sede?: string;
}
