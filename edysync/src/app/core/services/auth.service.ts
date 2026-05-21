// DCE — Diego Centeno Estuvo Acá
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';

export interface LoginResponse {
  valid?: boolean;
  user?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly LOGIN_URL = '/api/login';

  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.currentUserSubject.next(JSON.parse(storedUser));
    }
  }

  login(email: string, password: string): Observable<any> {
    return this.http.post<any>(this.LOGIN_URL, { email, password }).pipe(
      tap(res => {
        if (res.success) {
          localStorage.setItem('user', JSON.stringify(res.user));
          if (res.csrf_token) {
            localStorage.setItem('csrf_token', res.csrf_token);
          }
          this.currentUserSubject.next(res.user);
        }
      })
    );
  }

  logout(): Observable<any> {
    return this.http.post('/api/logout', {}).pipe(
      tap(() => {
        localStorage.removeItem('user');
        localStorage.removeItem('csrf_token');
        this.currentUserSubject.next(null);
      })
    );
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('user');
  }
}
