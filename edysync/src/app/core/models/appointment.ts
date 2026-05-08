export type AppointmentStatus = 'scheduled' | 'completed' | 'cancelled';
export type AttendanceStatus = 'pending' | 'present' | 'absent';

export interface Appointment {
  id: number;
  therapist_id: number;
  patient_id: number;
  title?: string;
  start_time: string;
  end_time?: string;
  status: AppointmentStatus;
  attendance?: AttendanceStatus;
  notes?: string;
  location?: string;
  therapy_type?: string;
  games?: string;
}

export interface CalendarEvent {
  id: number;
  title: string;
  start: string;
  end?: string;
  backgroundColor: string;
  borderColor: string;
  extendedProps: {
    therapist_id: number;
    patient_id: number;
    therapist: string;
    patient: string;
    status: AppointmentStatus;
    notes?: string;
  };
}

export interface BatchSessionPayload {
  therapist_id: number;
  patient_id: number;
  start_date: string;
  start_time: string;
  end_time: string;
  days: number[];
  title_prefix?: string;
  weeks?: number;
}
