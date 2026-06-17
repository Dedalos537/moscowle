import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/api-response';
import { User, CreateUserPayload } from '../models/user';
import { Sede, SedeAnalytics } from '../models/sede';
import { Payment, PatientPaymentStatus, DebtReport } from '../models/payment';
import { Appointment, CalendarEvent, BatchSessionPayload } from '../models/appointment';
import { Expense, TherapistFinancial, ContactMessage, TherapistStats, PatientStats } from '../models/expense';
import { Game } from '../models/game';
import { CSPReport, CSPReportFilter, CSPReportResponse } from '../models/csp-report';
import { AdminAPIToken, CreateTokenResponse } from '../models/api-token';
import { YapeTransaction, YapeImportStats, YapeDashboardStats } from '../models/yape';
import { AITrainingStatus, TrainResponse } from '../models/ai-training';

@Injectable({
  providedIn: 'root',
})
export class AdminService {
  constructor(private http: HttpClient) {}

  getOverview(): Observable<{ success: boolean; users: any[] }> {
    return this.http.get<{ success: boolean; users: any[] }>('/api/admin/list-users');
  }

  getUser(id: number): Observable<{ success: boolean; user: any }> {
    return this.http.get<{ success: boolean; user: any }>(`/api/admin/user/${id}`);
  }

  getAdminOverview(): Observable<{ success: boolean; data: { therapists: number; patients: number; sessions_total: number; avg_accuracy: number; avg_audit_compliance: number; audits_count: number } }> {
    return this.http.get<{ success: boolean; data: { therapists: number; patients: number; sessions_total: number; avg_accuracy: number; avg_audit_compliance: number; audits_count: number } }>('/admin/api/overview');
  }

  getUsers(role?: string): Observable<{ success: boolean; users: any[] }> {
    let params = new HttpParams();
    if (role) params = params.set('role', role);
    return this.http.get<{ success: boolean; users: any[] }>('/api/admin/list-users', { params });
  }

  createUser(data: CreateUserPayload): Observable<ApiResponse<{ user: User; temp_password: string }>> {
    return this.http.post<ApiResponse<{ user: User; temp_password: string }>>('/api/admin/create-user', data);
  }

  updateUser(data: Partial<User> & { id: number }): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/update-user', data);
  }

  deleteUser(id: number): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/delete-user', { id });
  }

  toggleUserStatus(userId: number): Observable<ApiResponse> {
    return this.http.post<ApiResponse>(`/admin/users/${userId}/toggle-status`, {});
  }

  resetPassword(userId: number, newPassword?: string): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/reset-password', { id: userId, new_password: newPassword });
  }

  assignTherapist(patientId: number, therapistIds: number[]): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/assign-therapist', { patient_id: patientId, therapist_ids: therapistIds });
  }

  getSedes(): Observable<Sede[]> {
    return this.http.get<Sede[]>('/api/admin/sedes');
  }

  createSede(data: { name: string; address?: string }): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/sedes', data);
  }

  updateSede(id: number, data: Partial<Sede>): Observable<ApiResponse> {
    return this.http.put<ApiResponse>(`/api/admin/sedes/${id}`, data);
  }

  getSedeAnalytics(id: number): Observable<any> {
    return this.http.get<any>(`/api/admin/sedes/${id}/analytics`);
  }

  getDebtReport(month?: string): Observable<{ success: boolean; data: DebtReport; error?: string }> {
    let params = new HttpParams();
    if (month) params = params.set('month', month);
    return this.http.get<{ success: boolean; data: DebtReport }>('/api/admin/deudores', { params });
  }

  registerPayment(formData: FormData): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/admin/payments/register', formData);
  }

  getPaymentHistory(userId: number): Observable<{ success: boolean; payments: Payment[]; patient: User }> {
    return this.http.get<{ success: boolean; payments: Payment[]; patient: User }>(`/admin/payments/history/${userId}`);
  }

  getAllPayments(): Observable<{ success: boolean; payments: any[] }> {
    return this.http.get<{ success: boolean; payments: any[] }>('/admin/api/payments/all');
  }

  deletePayment(paymentId: number): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/admin/payments/delete/' + paymentId, {});
  }

  updatePaymentSettings(patientId: number, data: { payment_amount?: number; payment_due_date?: string; payment_plan?: string }): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/admin/payments/settings', { patient_id: patientId, ...data });
  }

  getPaymentInfo(patientId: number): Observable<any> {
    return this.http.get<any>(`/admin/api/payment-info/${patientId}`);
  }

  getPatientsByTherapist(therapistId: number): Observable<{ id: number; username: string; email: string }[]> {
    return this.http.get<{ id: number; username: string; email: string }[]>('/api/patients', {
      params: new HttpParams().set('therapist_id', therapistId),
    });
  }

  getSessions(start?: string, end?: string, therapistId?: number): Observable<CalendarEvent[]> {
    let params = new HttpParams();
    if (start) params = params.set('start', start);
    if (end) params = params.set('end', end);
    if (therapistId) params = params.set('therapist_id', therapistId);
    return this.http.get<CalendarEvent[]>('/admin/api/sessions', { params });
  }

  batchCreateSessions(data: BatchSessionPayload): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/admin/api/sessions/batch', data);
  }

  updateSession(id: number, data: Partial<Appointment>): Observable<ApiResponse> {
    return this.http.put<ApiResponse>(`/admin/api/sessions/${id}`, data);
  }

  deleteSession(id: number): Observable<ApiResponse> {
    return this.http.delete<ApiResponse>(`/api/sessions/${id}`);
  }

  executeSmartAction(actionId: number): Observable<{ success: boolean; message: string }> {
    return this.http.post<{ success: boolean; message: string }>(`/admin/api/workflow/execute/${actionId}`, {});
  }

  broadcastMessage(data: { subject: string; body: string; target: string; receiver_id?: number }): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/messages/broadcast', data);
  }

  generateAIReport(): Observable<{ success: boolean; report: string }> {
    return this.http.post<{ success: boolean; report: string }>('/admin/generate-ia-report', {});
  }

  analyzeReceipt(file: File, patientId?: number): Observable<any> {
    const formData = new FormData();
    formData.append('receipt', file);
    if (patientId) formData.append('patient_id', String(patientId));
    return this.http.post<any>('/admin/analyze-receipt', formData);
  }

  getNotifications(): Observable<any[]> {
    return this.http.get<any[]>('/api/notifications');
  }

  markNotificationsRead(): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/notifications/mark-read', {});
  }

  markOneNotificationRead(notifId: number): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/notifications/mark-read', { id: notifId });
  }

  getExpenses(startDate?: string, endDate?: string, category?: string): Observable<{ success: boolean; data: Expense[] }> {
    let params = new HttpParams();
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);
    if (category) params = params.set('category', category);
    return this.http.get<{ success: boolean; data: Expense[] }>('/admin/api/expenses', { params });
  }

  getTherapistFinancials(month?: number, year?: number): Observable<{ success: boolean; data: TherapistFinancial[] }> {
    let params = new HttpParams();
    if (month) params = params.set('month', month);
    if (year) params = params.set('year', year);
    return this.http.get<{ success: boolean; data: TherapistFinancial[] }>('/admin/api/therapist-financials', { params });
  }

  createExpense(formData: FormData): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/admin/api/expenses/create', formData);
  }

  getContactMessages(): Observable<{ success: boolean; data: ContactMessage[] }> {
    return this.http.get<{ success: boolean; data: ContactMessage[] }>('/admin/api/contact-messages');
  }

  getFinancialSummary(): Observable<{ success: boolean; data: any }> {
    return this.http.get<{ success: boolean; data: any }>('/admin/api/financial-summary');
  }

  getTherapistStats(): Observable<{ success: boolean; data: TherapistStats[] }> {
    return this.http.get<{ success: boolean; data: TherapistStats[] }>('/admin/api/report-therapist-stats');
  }

  getPatientStats(): Observable<{ success: boolean; data: PatientStats[] }> {
    return this.http.get<{ success: boolean; data: PatientStats[] }>('/admin/api/report-patient-stats');
  }

  sendWeeklyReport(): Observable<{ success: boolean; message: string }> {
    return this.http.post<{ success: boolean; message: string }>('/admin/reports/send-weekly-summary', {});
  }

  exportPaymentsCsv(): Observable<Blob> {
    return this.http.get('/admin/reports/export-payments', { responseType: 'blob' });
  }


  getGames(): Observable<{ games: string[] }> {
    return this.http.get<{ games: string[] }>('/api/games');
  }

  uploadGame(name: string, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('name', name);
    formData.append('file', file);
    return this.http.post('/api/games/upload', formData);
  }

  deleteGame(name: string): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/admin/games/delete', { name });
  }

  generateGame(prompt: string, userId: number, name: string): Observable<any> {
    return this.http.post('/api/ai/generate_game', { prompt, user_id: userId, name });
  }


  getCSPReports(filter?: CSPReportFilter): Observable<CSPReportResponse> {
    let params = new HttpParams();
    if (filter?.directive) params = params.set('directive', filter.directive);
    if (filter?.blocked_uri) params = params.set('blocked_uri', filter.blocked_uri);
    if (filter?.since) params = params.set('since', filter.since);
    if (filter?.page) params = params.set('page', filter.page);
    if (filter?.per_page) params = params.set('per_page', filter.per_page);
    return this.http.get<CSPReportResponse>('/admin/api/csp-reports', { params });
  }

  exportCSPReportsCsv(filter?: CSPReportFilter): Observable<Blob> {
    let params = new HttpParams();
    if (filter?.directive) params = params.set('directive', filter.directive);
    if (filter?.blocked_uri) params = params.set('blocked_uri', filter.blocked_uri);
    if (filter?.since) params = params.set('since', filter.since);
    return this.http.get('/admin/csp-reports/export', { params, responseType: 'blob' });
  }


  getAPITokens(): Observable<{ tokens: AdminAPIToken[] }> {
    return this.http.get<{ tokens: AdminAPIToken[] }>('/admin/api/tokens/list');
  }

  createAPIToken(rotate: boolean = false): Observable<CreateTokenResponse> {
    return this.http.post<CreateTokenResponse>('/admin/api/tokens/create', { rotate });
  }

  deactivateAPIToken(tokenId: number): Observable<{ success: boolean }> {
    return this.http.post<{ success: boolean }>(`/admin/api/tokens/deactivate/${tokenId}`, {});
  }


  updateProfile(data: { username?: string; new_password?: string }): Observable<{ success: boolean; message?: string }> {
    return this.http.post<{ success: boolean; message?: string }>('/api/admin/profile', data);
  }


  importYapeFile(file: File): Observable<{ success: boolean; stats: YapeImportStats }> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<{ success: boolean; stats: YapeImportStats }>('/admin/yape/import', formData);
  }

  searchPatients(query: string): Observable<{ patients: Array<{ id: number; username: string; email: string; phone: string }> }> {
    return this.http.get<{ patients: Array<{ id: number; username: string; email: string; phone: string }> }>('/api/v1/search/patients', {
      params: new HttpParams().set('q', query),
    });
  }

  searchYape(query: string): Observable<{ results: YapeTransaction[] }> {
    return this.http.get<{ results: YapeTransaction[] }>('/admin/yape/search', {
      params: new HttpParams().set('q', query),
    });
  }

  getYapePending(): Observable<{ count: number; transactions: YapeTransaction[] }> {
    return this.http.get<{ count: number; transactions: YapeTransaction[] }>('/admin/yape/pending');
  }

  getYapeHistory(): Observable<YapeTransaction[]> {
    return this.http.get<YapeTransaction[]>('/admin/yape/history');
  }

  getYapeDashboard(): Observable<YapeDashboardStats> {
    return this.http.get<YapeDashboardStats>('/admin/yape/dashboard');
  }

  attachReceipt(operationNumber: string, file: File): Observable<any> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post(`/admin/yape/${operationNumber}/attach-receipt`, formData);
  }


  getAITrainingStatus(): Observable<AITrainingStatus> {
    return this.http.get<AITrainingStatus>('/admin/ai/status');
  }

  triggerAITraining(data?: { real_data?: number[][] }): Observable<TrainResponse> {
    return this.http.post<TrainResponse>('/admin/ai/train', data || {});
  }

  // --- PROGRAM UPLOADS / AUDITS ---
  getSessionAudit(sessionId: number): Observable<any> {
    return this.http.get<any>(`/api/sessions/${sessionId}/audit`);
  }

  uploadSessionProgram(sessionId: number, currentFile: File): Observable<any> {
    const formData = new FormData();
    formData.append('program_file', currentFile);
    return this.http.post<any>(`/api/sessions/${sessionId}/program`, formData);
  }

  deleteSessionProgram(sessionId: number): Observable<any> {
    return this.http.delete<any>(`/api/sessions/${sessionId}/program`);
  }

  getAuditStats(): Observable<any> {
    return this.http.get('/api/admin/audit-stats');
  }

  generateIAReport(): Observable<any> {
    return this.http.post('/admin/generate-ia-report', {});
  }


  getWeeklySummary(weekStart?: string): Observable<any> {
    let params = new HttpParams();
    if (weekStart) params = params.set('week_start', weekStart);
    return this.http.get<any>('/admin/api/weekly-summary', { params });
  }

  getDailyReports(start?: string, end?: string): Observable<any> {
    let params = new HttpParams();
    if (start) params = params.set('start', start);
    if (end) params = params.set('end', end);
    return this.http.get<any>('/admin/api/daily-reports', { params });
  }

  accumulateReports(): Observable<any> {
    return this.http.post<any>('/admin/api/reports/accumulate', {});
  }


  getMonthlySummary(year?: number, month?: number): Observable<any> {
    let params = new HttpParams();
    if (year) params = params.set('year', year);
    if (month) params = params.set('month', month);
    return this.http.get<any>('/admin/api/reports/monthly', { params });
  }

  getQuarterlySummary(year?: number, quarter?: number): Observable<any> {
    let params = new HttpParams();
    if (year) params = params.set('year', year);
    if (quarter) params = params.set('quarter', quarter);
    return this.http.get<any>('/admin/api/reports/quarterly', { params });
  }

  generateAllWeeklyReports(weekStart?: string): Observable<any> {
    let params = new HttpParams();
    if (weekStart) params = params.set('week_start', weekStart);
    return this.http.post<any>('/admin/api/reports/generate-all-weekly', {}, { params });
  }

  generateMonthlyReports(year?: number, month?: number): Observable<any> {
    let params = new HttpParams();
    if (year) params = params.set('year', year);
    if (month) params = params.set('month', month);
    return this.http.post<any>('/admin/api/reports/generate-monthly', {}, { params });
  }

  generateQuarterlyReports(year?: number, quarter?: number): Observable<any> {
    let params = new HttpParams();
    if (year) params = params.set('year', year);
    if (quarter) params = params.set('quarter', quarter);
    return this.http.post<any>('/admin/api/reports/generate-quarterly', {}, { params });
  }

  getTherapistEfficiency(therapistId?: number): Observable<any> {
    let params = new HttpParams();
    if (therapistId) params = params.set('therapist_id', therapistId);
    return this.http.get<any>('/admin/api/therapist-efficiency', { params });
  }

}
