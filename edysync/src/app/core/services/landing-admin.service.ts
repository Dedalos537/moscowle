import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

/** Contenido de la landing pública (centrojuanpabloii.com). La forma la valida el backend; aquí se edita como datos. */
export type LandingContent = Record<string, any>;

export type LeadChannel = 'form' | 'whatsapp' | 'call';
export type LeadStatus = 'new' | 'contacted' | 'scheduled' | 'discarded';

export interface LandingLead {
  id: number;
  channel: LeadChannel;
  name: string | null;
  phone: string | null;
  email: string | null;
  patient_age: string | null;
  service: string | null;
  preferred_time: 'manana' | 'tarde' | 'cualquiera' | null;
  message: string | null;
  status: LeadStatus;
  staff_note: string | null;
  source: string | null;
  handled_by: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface LandingVersion {
  id: number;
  note: string | null;
  created_at: string | null;
  author: string | null;
}

export interface LandingContentResponse {
  success: boolean;
  content: LandingContent;
  version: number;
  versions: LandingVersion[];
  default?: LandingContent;
}

export interface LandingStats {
  last_30_days: Record<LeadChannel, number>;
  by_status: Record<LeadStatus, number>;
}

/** API de la landing (/api/landing): contenido versionado y bandeja de solicitudes de evaluación. */
@Injectable({ providedIn: 'root' })
export class LandingAdminService {
  private http = inject(HttpClient);

  content(): Observable<LandingContentResponse> {
    return this.http.get<LandingContentResponse>('/api/landing/admin/content');
  }

  publish(content: LandingContent, baseVersion: number, note: string): Observable<LandingContentResponse> {
    return this.http.put<LandingContentResponse>('/api/landing/admin/content', { content, base_version: baseVersion, note });
  }

  restore(versionId: number): Observable<LandingContentResponse> {
    return this.http.post<LandingContentResponse>(`/api/landing/admin/content/restore/${versionId}`, {});
  }

  leads(filter: { status?: string; q?: string; page?: number }): Observable<{ success: boolean; leads: LandingLead[]; total: number }> {
    let params = new HttpParams().set('contact', '1').set('per_page', '50');
    if (filter.status) params = params.set('status', filter.status);
    if (filter.q) params = params.set('q', filter.q);
    if (filter.page) params = params.set('page', String(filter.page));
    return this.http.get<{ success: boolean; leads: LandingLead[]; total: number }>('/api/landing/admin/leads', { params });
  }

  updateLead(id: number, patch: { status?: LeadStatus; staff_note?: string }): Observable<{ success: boolean; lead: LandingLead }> {
    return this.http.patch<{ success: boolean; lead: LandingLead }>(`/api/landing/admin/leads/${id}`, patch);
  }

  stats(): Observable<{ success: boolean } & LandingStats> {
    return this.http.get<{ success: boolean } & LandingStats>('/api/landing/admin/stats');
  }
}
