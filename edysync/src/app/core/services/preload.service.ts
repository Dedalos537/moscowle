import { Injectable } from '@angular/core';
import { HttpClient, HttpContext, HttpContextToken } from '@angular/common/http';
import { environment } from '../../../environments/environment';

export const SILENT_HTTP = new HttpContextToken<boolean>(() => false);

const COMMON = [
  '/api/chats',
  '/api/contacts',
  '/api/notifications',
  '/api/notifications/count',
  '/api/notifications/preferences',
  '/api/messages/unread-count'
];

const ADMIN = [
  '/api/admin/list-users',
  '/api/admin/list-users?role=terapista',
  '/api/admin/list-users?role=jugador',
  '/admin/api/overview',
  '/api/admin/sedes',
  '/api/admin/sedes/stats',
  '/api/admin/sedes/active',
  '/api/admin/patient-groups',
  '/api/admin/deudores?month=all',
  '/admin/api/financial-summary',
  '/admin/api/expenses',
  '/admin/api/payments/all',
  '/admin/api/installments/due',
  '/admin/api/installments/upcoming?days=7',
  '/api/admin/audit-stats',
  '/admin/api/report-therapist-stats',
  '/admin/api/report-patient-stats',
  '/admin/api/therapist-efficiency',
  '/api/games',
  '/admin/api/csp-reports?page=1&per_page=25',
  '/admin/api/tokens/list',
  '/admin/yape/dashboard',
  '/admin/yape/pending',
  '/admin/yape/history',
  '/admin/ai/status',
  '/admin/api/railway-metrics',
  '/admin/api/app-metrics',
  '/admin/api/logs?limit=200',
  '/api/incidents/dashboard',
  '/api/incidents?page=1&per_page=15',
  '/admin/api/admin/reset-actions?status=awaiting_approval'
];

const THERAPIST = [
  '/api/therapist/dashboard',
  '/therapist/api/dashboard-stats',
  '/therapist/api/profile',
  '/therapist/api/reports/overview',
  '/therapist/api/reports/detailed',
  '/therapist/api/analytics',
  '/api/patients',
  '/api/games',
  '/api/incidents/my?page=1&per_page=20'
];

const PATIENT = [
  '/patient/api/dashboard',
  '/patient/api/sessions',
  '/patient/api/progress',
  '/patient/api/payments',
  '/patient/api/my-therapist',
  '/api/incidents/my?page=1&per_page=20'
];

const BY_ROLE: Record<string, string[]> = {
  admin: [...ADMIN, ...COMMON],
  supervisor: [...ADMIN, ...COMMON],
  terapista: [...THERAPIST, ...COMMON],
  jugador: [...PATIENT, ...COMMON]
};

@Injectable({
  providedIn: 'root'
})
export class PreloadService {
  private doneFor = new Set<string>();

  constructor(private http: HttpClient) {}

  preloadFor(role: string): void {
    if (!role || this.doneFor.has(role) || !environment.preload) {
      return;
    }
    this.doneFor.add(role);
    const urls = BY_ROLE[role];
    if (!urls) {
      return;
    }
    const context = new HttpContext().set(SILENT_HTTP, true);
    const unique = new Set<string>(urls);
    if (role === 'terapista') {
      unique.add(this.currentAppointmentsUrl());
    }
    for (const url of unique) {
      this.http.get(url, { context }).subscribe({ error: () => {} });
    }
  }

  private currentAppointmentsUrl(): string {
    const now = new Date();
    return `/therapist/api/appointments/${now.getFullYear()}/${now.getMonth() + 1}`;
  }
}
