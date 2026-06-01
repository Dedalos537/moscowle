import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface LogEntry {
  timestamp: string;
  level: string;
  logger: string;
  message: string;
  short_message: string;
  exc_info?: string[];
}

export interface LogsResponse {
  success: boolean;
  logs: LogEntry[];
}

@Injectable({
  providedIn: 'root',
})
export class LogViewerService {
  constructor(private http: HttpClient) {}

  getLogs(level?: string, limit?: number, search?: string): Observable<LogsResponse> {
    let params = new HttpParams();
    if (level) params = params.set('level', level);
    if (limit) params = params.set('limit', limit);
    if (search) params = params.set('search', search);
    return this.http.get<LogsResponse>('/admin/api/logs', { params });
  }
}
