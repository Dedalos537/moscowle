import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiResponse } from '../../models/api-response';

export interface PatientDashboardData {
  player_stats: {
    total_sessions: number;
    avg_accuracy: number;
    avg_time: number;
    games_played: number;
  };
  today_sessions: {
    id: number;
    title: string;
    start_time: string;
    therapist: string;
    status: string;
  }[];
  payment_status: {
    is_overdue: boolean;
    days_overdue: number;
    next_due_date: string;
    pending_amount: number;
  };
}

export interface PatientSession {
  id: number;
  title: string;
  start_time: string;
  end_time: string;
  therapist: string;
  status: string;
  attendance: string;
}

export interface PatientProgress {
  labels: string[];
  accuracy_data: number[];
  time_data: number[];
  weekly_summary: string;
  avg_accuracy: number;
  achievements: { title: string; name: string; achieved: boolean; date?: string }[];
}

export interface PatientPayment {
  id: number;
  amount: number;
  date: string;
  method: string;
  status: string;
  reference?: string;
  concept?: string;
}

export interface MyTherapistInfo {
  id: number;
  username: string;
  email: string;
  phone?: string;
  bio?: string;
  specialties?: string[];
  full_name?: string;
}

@Injectable({ providedIn: 'root' })
export class PatientService {
  constructor(private http: HttpClient) {}

  getDashboard(): Observable<{ success: boolean; data: PatientDashboardData }> {
    return this.http.get<{ success: boolean; data: PatientDashboardData }>('/patient/api/dashboard');
  }

  getSessions(): Observable<{ success: boolean; data: PatientSession[] }> {
    return this.http.get<{ success: boolean; data: PatientSession[] }>('/patient/api/sessions');
  }

  getProgress(): Observable<{ success: boolean; data: PatientProgress }> {
    return this.http.get<{ success: boolean; data: PatientProgress }>('/patient/api/progress');
  }

  getPayments(): Observable<{ success: boolean; data: PatientPayment[] }> {
    return this.http.get<{ success: boolean; data: PatientPayment[] }>('/patient/api/payments');
  }

  getMyTherapist(): Observable<{ success: boolean; data: MyTherapistInfo }> {
    return this.http.get<{ success: boolean; data: MyTherapistInfo }>('/patient/api/my-therapist');
  }

  getMessages(): Observable<{ success: boolean; messages: any[] }> {
    return this.http.get<{ success: boolean; messages: any[] }>('/patient/api/messages');
  }

  sendMessage(therapistId: number, body: string, file?: File | null): Observable<ApiResponse> {
    const formData = new FormData();
    formData.append('receiver_id', String(therapistId));
    formData.append('body', body);
    if (file) {
      formData.append('file', file);
    }
    return this.http.post<ApiResponse>('/patient/api/messages/send', formData);
  }

  updateProfile(data: { username?: string; phone?: string; new_password?: string }): Observable<ApiResponse> {
    return this.http.post<ApiResponse>('/patient/api/profile/update', data);
  }
}
