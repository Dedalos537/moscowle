import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../models/api-response';
import { User, CreateUserPayload } from '../models/user';
import { Sede, SedeAnalytics } from '../models/sede';
import { Payment, PatientPaymentStatus, DebtReport } from '../models/payment';
import { Appointment, CalendarEvent, BatchSessionPayload } from '../models/appointment';
import { Expense, TherapistFinancial, ContactMessage, TherapistStats, PatientStats } from '../models/expense';

@Injectable({
  providedIn: 'root',
})
export class AdminService {
  constructor(private http: HttpClient) {}

  getOverview(): Observable<{ success: boolean; users: { id: number; email: string; username: string; role: string }[] }> {
    return this.http.get<{ success: boolean; users: { id: number; email: string; username: string; role: string }[] }>('/api/admin/list-users');
  }

  getUsers(role?: string): Observable<{ success: boolean; users: { id: number; email: string; username: string; role: string }[] }> {
    let params = new HttpParams();
    if (role) params = params.set('role', role);
    return this.http.get<{ success: boolean; users: { id: number; email: string; username: string; role: string }[] }>('/api/admin/list-users', { params });
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

  getSedeAnalytics(id: number): Observable<ApiResponse<SedeAnalytics>> {
    return this.http.get<ApiResponse<SedeAnalytics>>(`/api/admin/sedes/${id}/analytics`);
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
    return this.http.delete<ApiResponse>(`/admin/api/sessions/${id}`);
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

  analyzeReceipt(file: File): Observable<any> {
    const formData = new FormData();
    formData.append('receipt', file);
    return this.http.post<any>('/admin/analyze-receipt', formData);
  }

  getNotifications(): Observable<any[]> {
    return this.http.get<any[]>('/api/notifications');
  }

  markNotificationsRead(): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/api/notifications/mark-read', {});
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
}
