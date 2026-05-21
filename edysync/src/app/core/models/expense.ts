// DCE — Diego Centeno Estuvo Acá
export interface Expense {
  id: number;
  category: string;
  amount: number;
  date: string;
  description?: string;
  method?: string;
  therapist_id?: number;
  therapist?: { id: number; username: string };
  receipt_image_path?: string;
  created_at: string;
}

export interface CreateExpensePayload {
  category: string;
  amount: number;
  date?: string;
  description?: string;
  method?: string;
  therapist_id?: number | null;
  receipt?: File;
}

export interface TherapistFinancial {
  therapist: { id: number; username: string; salary_base: number; contract_hours: number };
  rate: number;
  contract_hours: number;
  worked_hours: number;
  projected_pay: number;
  paid: number;
  balance: number;
}

export interface ContactMessage {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  subject?: string;
  message: string;
  service_interest?: string;
  urgency: string;
  status: string;
  created_at: string;
}

export interface TherapistStats {
  id: number;
  name: string;
  email: string;
  sessions: number;
  avg_accuracy: number;
}

export interface PatientStats {
  id: number;
  name: string;
  email: string;
  plays: number;
  avg_accuracy: number;
}
