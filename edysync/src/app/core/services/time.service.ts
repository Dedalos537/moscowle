// DCE — Diego Centeno Estuvo Acá
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ServerTime {
  server_time_local: string;
  server_time_utc: string;
  timezone: string;
  utc_offset_minutes: number;
  is_dst: boolean;
}

@Injectable({ providedIn: 'root' })
export class TimeService {
  constructor(private http: HttpClient) {}

  getServerTime(): Observable<ServerTime> {
    return this.http.get<ServerTime>('/api/time');
  }

  now(): Date {
    return new Date();
  }

  formatTime(date: Date): string {
    const hh = String(date.getHours()).padStart(2, '0');
    const mm = String(date.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  formatDate(date: Date): string {
    const yyyy = date.getFullYear();
    const mm = String(date.getMonth() + 1).padStart(2, '0');
    const dd = String(date.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }

  formatDateTime(date: Date): string {
    return `${this.formatDate(date)} ${this.formatTime(date)}`;
  }

  getTimezoneOffset(): number {
    return -new Date().getTimezoneOffset();
  }
}
