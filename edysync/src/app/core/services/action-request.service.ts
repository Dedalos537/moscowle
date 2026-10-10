import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export type RequestKind = 'sessions' | 'patient' | 'group';
export type RequestStatus = 'pending' | 'approved' | 'rejected';

export interface ActionRequest {
  id: number;
  kind: RequestKind;
  payload: Record<string, unknown>;
  summary: string;
  status: RequestStatus;
  requester_id: number;
  requester_name: string | null;
  reviewer_name: string | null;
  review_note: string | null;
  result: Record<string, unknown> | null;
  last_error: string | null;
  created_at: string | null;
  resolved_at: string | null;
}

export interface RequestOptions {
  patients: { id: number; username: string }[];
  groups: { id: number; name: string; member_count: number; start_time: string | null; end_time: string | null }[];
  sedes: { id: number; name: string }[];
}

export const REQUEST_KIND_LABEL: Record<RequestKind, string> = {
  sessions: 'Programar sesiones',
  patient: 'Alta de paciente',
  group: 'Nuevo grupo',
};

/** Solicitudes de terapeutas que aprueba la coordinación (como el cambio de contraseña). */
@Injectable({ providedIn: 'root' })
export class ActionRequestService {
  private http = inject(HttpClient);

  options(): Observable<RequestOptions & { success: boolean }> {
    return this.http.get<RequestOptions & { success: boolean }>('/api/requests/options');
  }

  create(kind: RequestKind, payload: Record<string, unknown>): Observable<{ success: boolean; request: ActionRequest }> {
    return this.http.post<{ success: boolean; request: ActionRequest }>('/api/requests', { kind, payload });
  }

  mine(): Observable<{ success: boolean; requests: ActionRequest[] }> {
    return this.http.get<{ success: boolean; requests: ActionRequest[] }>('/api/requests/mine');
  }

  list(status?: RequestStatus): Observable<{ success: boolean; requests: ActionRequest[]; pending: number }> {
    const params = status ? new HttpParams().set('status', status) : undefined;
    return this.http.get<{ success: boolean; requests: ActionRequest[]; pending: number }>('/api/requests', { params });
  }

  approve(id: number): Observable<{ success: boolean; request: ActionRequest }> {
    return this.http.post<{ success: boolean; request: ActionRequest }>(`/api/requests/${id}/approve`, {});
  }

  reject(id: number, note: string): Observable<{ success: boolean; request: ActionRequest }> {
    return this.http.post<{ success: boolean; request: ActionRequest }>(`/api/requests/${id}/reject`, { note });
  }
}
