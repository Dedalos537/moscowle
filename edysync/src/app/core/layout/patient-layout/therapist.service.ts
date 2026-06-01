import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../models/api-response';
import { CalendarEvent } from '../../models/appointment';

export interface TherapistProfileData {
  id: number;
  username: string;
  email: string;
  timezone: string;
  created_at: string | null;
  patients_count: number;
  sessions_count: number;
  upcoming_appointments: number;
}

export interface Conversation {
  user_id: number;
  username: string;
  email: string;
  last_message: string | null;
  unread_count: number;
}

export interface MessageThread {
  other_user: { id: number; username: string; email: string };
  messages: MessageItem[];
}

export interface MessageItem {
  id: number;
  sender_id: number;
  receiver_id: number;
  body: string;
  file_url: string | null;
  file_type: string | null;
  created_at: string;
  is_read: boolean;
}

export interface DashboardStats {
  sessions_today: number;
  completed_sessions: number;
  pending_sessions: number;
  active_patients: number;
}

export interface PatientInfo {
  id: number;
  username: string;
  email: string;
}

@Injectable({
  providedIn: 'root',
})
export class TherapistService {
  constructor(private http: HttpClient) {}

  getProfile(): Observable<TherapistProfileData> {
    return this.http.get<TherapistProfileData>('/therapist/api/profile');
  }

  updateProfile(data: { username?: string; timezone?: string; new_password?: string }): Observable<{ success: boolean; message: string }> {
    return this.http.put<{ success: boolean; message: string }>('/therapist/api/profile', data);
  }

  getDashboardStats(): Observable<DashboardStats> {
    return this.http.get<DashboardStats>('/therapist/api/dashboard-stats');
  }

  getConversations(): Observable<{ conversations: Conversation[] }> {
    return this.http.get<{ conversations: Conversation[] }>('/therapist/api/conversations');
  }

  getMessageThread(userId: number): Observable<MessageThread> {
    return this.http.get<MessageThread>(`/therapist/api/messages/${userId}`);
  }

  sendMessage(receiverId: number, body: string, file?: File | null): Observable<any> {
    const formData = new FormData();
    formData.append('receiver_id', String(receiverId));
    formData.append('body', body);
    if (file) {
      formData.append('file', file);
    }
    return this.http.post('/api/messages/send', formData);
  }

  getUnreadCount(): Observable<{ count: number }> {
    return this.http.get<{ count: number }>('/api/messages/unread-count');
  }

  getPatients(): Observable<PatientInfo[]> {
    return this.http.get<PatientInfo[]>('/api/patients');
  }

  getSessions(start?: string, end?: string): Observable<CalendarEvent[]> {
    let params = new HttpParams();
    if (start) params = params.set('start', start);
    if (end) params = params.set('end', end);
    return this.http.get<CalendarEvent[]>('/api/sessions', { params });
  }

  createSession(data: {
    patient_id: number;
    title: string;
    start_time: string;
    end_time: string;
    status?: string;
    notes?: string;
  }): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/sessions', data);
  }

  updateSession(id: number, data: Partial<{ title: string; start_time: string; end_time: string; status: string; notes: string }>): Observable<ApiResponse> {
    return this.http.put<ApiResponse>(`/api/sessions/${id}`, data);
  }

  deleteSession(id: number): Observable<ApiResponse> {
    return this.http.delete<ApiResponse>(`/api/sessions/${id}`);
  }

  getGames(): Observable<{ games: string[] }> {
    return this.http.get<{ games: string[] }>('/api/games');
  }

  getGameUrl(filename: string): string {
    return `/static/games/${filename}`;
  }


  getSession(id: number): Observable<any> {
    return this.http.get<any>(`/api/sessions/${id}`);
  }

  updateAttendance(id: number, attendance: string): Observable<any> {
    return this.http.put<any>(`/api/sessions/${id}`, { attendance });
  }

  saveNotes(id: number, notes: string): Observable<any> {
    return this.http.put<any>(`/api/sessions/${id}`, { notes });
  }


  uploadSessionImage(appointmentId: number, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('image', file);
    formData.append('image_type', 'session_photo');
    return this.http.post<any>(`/api/appointments/${appointmentId}/upload_image`, formData);
  }

  deleteSessionImage(appointmentId: number, imageId: number): Observable<any> {
    return this.http.delete<any>(`/api/appointments/${appointmentId}/images/${imageId}`);
  }


  uploadAudioChunk(appointmentId: number, blob: Blob, chunkNum: number): Observable<any> {
    const formData = new FormData();
    formData.append('audio_file', blob, `session_${appointmentId}_chunk${chunkNum}_${Date.now()}.webm`);
    return this.http.post<any>(`/api/sessions/${appointmentId}/audio`, formData);
  }


  startRecording(sessionId: number): Observable<any> {
    return this.http.post<any>(`/api/sessions/${sessionId}/start-recording`, {});
  }

  analyzeAttendance(sessionId: number): Observable<any> {
    return this.http.post<any>(`/api/sessions/${sessionId}/analyze-attendance`, {});
  }

  markAbsent(sessionId: number): Observable<any> {
    return this.http.post<any>(`/api/sessions/${sessionId}/mark-absent`, {});
  }


  submitFeedback(sessionId: number, data: { engagement: number | null; progress: number | null; notes: string }): Observable<any> {
    return this.http.post<any>(`/api/sessions/${sessionId}/feedback`, data);
  }


  getSessionAudit(sessionId: number): Observable<any> {
    return this.http.get<any>(`/api/sessions/${sessionId}/audit`);
  }

  triggerAudit(sessionId: number): Observable<any> {
    return this.http.post<any>(`/api/sessions/${sessionId}/audit`, {});
  }

  downloadReportDocx(sessionId: number): Observable<Blob> {
    return this.http.get(`/api/sessions/${sessionId}/report-docx`, { responseType: 'blob' });
  }

  getSessionProgram(sessionId: number): Observable<any> {
    return this.http.get<any>(`/api/sessions/${sessionId}/program`);
  }


  getAnalytics(): Observable<ApiResponse<AnalyticsData>> {
    return this.http.get<ApiResponse<AnalyticsData>>('/therapist/api/analytics');
  }

  getReportsOverview(): Observable<ApiResponse<ReportsOverview>> {
    return this.http.get<ApiResponse<ReportsOverview>>('/therapist/api/reports/overview');
  }

  getDetailedReports(start?: string, end?: string): Observable<ApiResponse<PatientReport[]>> {
    let params = new HttpParams();
    if (start) params = params.set('start', start);
    if (end) params = params.set('end', end);
    return this.http.get<ApiResponse<PatientReport[]>>('/therapist/api/reports/detailed', { params });
  }

  getTherapistAppointments(month: number, year: number): Observable<ApiResponse<CalendarEvent[]>> {
    return this.http.get<ApiResponse<CalendarEvent[]>>(`/therapist/api/appointments/${year}/${month}`);
  }

  getPatientStats(): Observable<ApiResponse<PatientStatsReport[]>> {
    return this.http.get<ApiResponse<PatientStatsReport[]>>('/therapist/api/patient-stats');
  }


  generateWeeklyReport(patientId: number): Observable<any> {
    return this.http.post<any>('/reports/generate-weekly', { patient_id: patientId });
  }

  getWeeklyReport(patientId: number): Observable<any> {
    return this.http.get<any>(`/reports/weekly/${patientId}`);
  }
}

export interface AnalyticsData {
  kpi: {
    adaptations_count: number;
    avg_accuracy: number;
    success_rate: number;
    active_models: number;
  };
  difficulty_matrix: DifficultyMatrixEntry[];
  prediction_distribution: PredictionDistribution[];
  model_confidence: ModelConfidence[];
  recent_adaptations: Adaptation[];
}

export interface DifficultyMatrixEntry {
  game: string;
  levels: DifficultyLevel[];
}

export interface DifficultyLevel {
  level: string;
  accuracy: number;
  count: number;
  name?: string;
}

export interface PredictionDistribution {
  label: PredictionType;
  value: number;
  percentage?: number;
}

export type PredictionType = 'Avanzar' | 'Apoyar' | 'Mantener' | string;

export interface ModelConfidence {
  model: string;
  confidence: number;
}

export interface Adaptation {
  date: string;
  description: string;
  impact: 'positive' | 'neutral' | 'negative';
  patient_name: string;
  type: string;
  status: string;
  created_at: string;
}

export interface ReportsOverview {
  improvement_rate: number;
  avg_session_time_minutes: number;
  completed_objectives: number;
  active_patients: number;
}

export interface PatientReport {
  patient_id: number;
  patient_name: string;
  sessions_count: number;
  avg_accuracy: number;
  total_plays: number;
}

export interface PatientStatsReport {
  patient_id: number;
  patient_name: string;
  total_sessions: number;
  completed_sessions: number;
  avg_accuracy: number;
  improvement: number;
}
