import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface KanbanTask {
  id: number;
  title: string;
  description: string;
  therapy_type: string;
  session_id: number | null;
  max_minutes: number;
  column: 'todo' | 'in-progress' | 'review' | 'done';
  position: number;
  timer_start: string | null;
  is_expired: boolean;
  priority: 1 | 2 | 3;
  assigned_to_id: number | null;
  assigned_to_name: string | null;
  created_by_id: number;
  created_by_name: string | null;
  sede_id: number | null;
  sede_name: string | null;
  is_active: boolean;
  attachment_count: number;
  created_at: string;
  updated_at: string;
  attachments?: KanbanAttachment[];
}

export interface KanbanAttachment {
  id: number;
  filename: string;
  mimetype: string;
  size: number;
  task_id: number;
  data?: string;
  created_at: string;
}

export interface KanbanStats {
  total: number;
  by_column: Record<string, number>;
  expired: number;
  unassigned: number;
}

@Injectable({ providedIn: 'root' })
export class KanbanService {
  private api = '/api/kanban';

  constructor(private http: HttpClient) {}

  getTasks(filters?: { therapy_type?: string; priority?: number; assigned_to?: number }): Observable<KanbanTask[]> {
    let params: any = {};
    if (filters?.therapy_type) params.therapy_type = filters.therapy_type;
    if (filters?.priority) params.priority = filters.priority;
    if (filters?.assigned_to) params.assigned_to = filters.assigned_to;
    return this.http.get<KanbanTask[]>(`${this.api}/tasks`, { params });
  }

  createTask(data: Partial<KanbanTask>): Observable<KanbanTask> {
    return this.http.post<KanbanTask>(`${this.api}/tasks`, data);
  }

  updateTask(id: number, data: Partial<KanbanTask>): Observable<KanbanTask> {
    return this.http.patch<KanbanTask>(`${this.api}/tasks/${id}`, data);
  }

  deleteTask(id: number): Observable<any> {
    return this.http.delete(`${this.api}/tasks/${id}`);
  }

  extendTimer(id: number, minutes: number): Observable<KanbanTask> {
    return this.http.patch<KanbanTask>(`${this.api}/tasks/${id}/extend`, { minutes });
  }

  getAttachments(taskId: number): Observable<KanbanAttachment[]> {
    return this.http.get<KanbanAttachment[]>(`${this.api}/tasks/${taskId}/attachments`);
  }

  uploadAttachment(taskId: number, file: File): Observable<KanbanAttachment> {
    return new Observable(subscriber => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = reader.result as string;
        this.http.post<KanbanAttachment>(`${this.api}/tasks/${taskId}/attachments`, {
          filename: file.name,
          mimetype: file.type,
          data: base64,
        }).subscribe(subscriber);
      };
      reader.onerror = () => subscriber.error(reader.error);
      reader.readAsDataURL(file);
    });
  }

  deleteAttachment(taskId: number, attachmentId: number): Observable<any> {
    return this.http.delete(`${this.api}/tasks/${taskId}/attachments`, {
      params: { attachmentId: attachmentId.toString() },
    });
  }

  getAttachmentData(attId: number): Observable<KanbanAttachment> {
    return this.http.get<KanbanAttachment>(`${this.api}/attachments/${attId}`);
  }

  getStats(): Observable<KanbanStats> {
    return this.http.get<KanbanStats>(`${this.api}/stats`);
  }
}
