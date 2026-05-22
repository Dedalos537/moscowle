export type UserRole = 'admin' | 'terapista' | 'jugador';
export type AccountStatus = 'active' | 'inactive' | 'retired' | 'debtor';

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  account_status: AccountStatus;
  phone?: string;
  date_of_birth?: string;
  guardian_name?: string;
  guardian_contact?: string;
  document_number?: string;
  therapy_goals?: string;
  notes?: string;
  timezone?: string;

  sede_id?: number;
  assigned_sedes?: SedeBrief[];
  assigned_therapist_id?: number;
  therapists?: UserBrief[];
  associated_patients?: UserBrief[];

  payment_plan?: string;
  payment_due_date?: string;
  payment_amount?: number;
  payment_day?: number;
  sessions_total?: number;
  sessions_attended?: number;
  sessions_remaining?: number;
  session_cost?: number;
  plan_type?: string;

  has_second_shift?: boolean;
  modality_2?: number;
  payment_amount_2?: number;
  sessions_total_2?: number;
  sessions_attended_2?: number;
  session_cost_2?: number;
  plan_type_2?: string;

  salary_base?: number;
  contract_hours?: number;
  work_start_time?: string;
  work_end_time?: string;
  work_days?: string;

  created_at: string;
  updated_at?: string;
}

export interface UserBrief {
  id: number;
  username: string;
  email?: string;
  role?: UserRole;
}

export interface SedeBrief {
  id: number;
  name: string;
}

export interface CreateUserPayload {
  role: UserRole;
  email?: string;
  username?: string;
  password?: string;
  phone?: string;
  guardian?: string;
  sede_id?: number;
  sede_ids?: number[];
  therapist_id?: number;
  modality?: number;
  payment_amount?: number;
  payment_frequency?: string;
  plan_type?: string;
  start_date?: string;
  start_time?: string;
  days_of_week?: number[];
  generate_schedule?: boolean;
  salary_base?: number;
  contract_hours?: number;
}
