import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Incident {
  id: number;
  titulo: string;
  descripcion: string;
  categoria: string;
  subcategoria: string | null;
  impacto: number;
  urgencia: number;
  prioridad: number;
  estado: string;
  responsable_id: number | null;
  responsable_name: string | null;
  user_id: number;
  user_name: string | null;
  appointment_id: number | null;
  evidencia_tipo: string;
  fecha_creacion: string;
  fecha_limite_sla: string | null;
  fecha_resolucion: string | null;
  escalamiento_nivel: number;
  horas_invertidas: number;
  esta_vencido: boolean;
  horas_restantes_sla: number | null;
  post_mortem: string | null;
  causa_raiz: string | null;
  lecciones_aprendidas: string | null;
}

export interface IncidentDetail extends Incident {
  evidencia_original: string;
  evidencia_metadata: string | null;
  historial: IncidentHistoryEntry[];
  comentarios: IncidentComment[];
}

export interface IncidentHistoryEntry {
  id: number;
  estado_anterior: string | null;
  estado_nuevo: string;
  comentario: string | null;
  changed_by: string | null;
  changed_at: string | null;
  escalamiento_nivel: number | null;
}

export interface IncidentComment {
  id: number;
  contenido: string;
  es_interno: boolean;
  autor: string | null;
  created_at: string | null;
}

export interface IncidentDashboard {
  total_abiertos: number;
  vencidos: number;
  resueltos_hoy: number;
  sla_compliance_7d: number;
  por_estado: Record<string, number>;
  por_categoria: Record<string, number>;
  por_prioridad: Record<string, number>;
}

export interface IncidentListResponse {
  incidentes: Incident[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

@Injectable({ providedIn: 'root' })
export class IncidentService {
  private base = '/api/incidents';

  constructor(private http: HttpClient) {}

  getDashboard(): Observable<IncidentDashboard> {
    return this.http.get<IncidentDashboard>(`${this.base}/dashboard`);
  }

  listIncidents(filters: {
    estado?: string;
    prioridad?: number;
    categoria?: string;
    responsable_id?: number;
    desde?: string;
    hasta?: string;
    page?: number;
    per_page?: number;
  } = {}): Observable<IncidentListResponse> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<IncidentListResponse>(this.base, { params });
  }

  getIncident(id: number): Observable<IncidentDetail> {
    return this.http.get<IncidentDetail>(`${this.base}/${id}`);
  }

  createIncident(data: {
    titulo: string;
    descripcion: string;
    categoria: string;
    subcategoria?: string;
    impacto?: number;
    urgencia?: number;
    prioridad?: number;
    appointment_id?: number;
    evidencia_tipo?: string;
    evidencia_original?: string;
  }): Observable<IncidentDetail> {
    return this.http.post<IncidentDetail>(this.base, data);
  }

  getMyIncidents(page = 1, perPage = 20): Observable<IncidentListResponse> {
    let params = new HttpParams().set('page', String(page)).set('per_page', String(perPage));
    return this.http.get<IncidentListResponse>(`${this.base}/my`, { params });
  }

  getMetrics(): Observable<any> {
    return this.http.get<any>(`${this.base}/metrics`);
  }

  updateStatus(id: number, estado: string, comentario?: string): Observable<IncidentDetail> {
    return this.http.put<IncidentDetail>(`${this.base}/${id}/status`, { estado, comentario });
  }

  addComment(id: number, contenido: string, es_interno = false): Observable<any> {
    return this.http.post(`${this.base}/${id}/comments`, { contenido, es_interno });
  }

  assignIncident(id: number, responsable_id: number): Observable<IncidentDetail> {
    return this.http.put<IncidentDetail>(`${this.base}/${id}/assign`, { responsable_id });
  }
}
