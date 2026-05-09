import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, map, switchMap, tap } from 'rxjs';

export interface LoginResponse {
  valid?: boolean;
  user?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly LOGIN_URL = '/login';

  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient) {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.currentUserSubject.next(JSON.parse(storedUser));
    }
  }

  login(email: string, password: string): Observable<any> {
    return this.http.get(this.LOGIN_URL, { responseType: 'text' }).pipe(
      switchMap((htmlPage: string) => {
        const match = htmlPage.match(/name="csrf_token"\s+value="([^"]+)"/);
        const csrfToken = match ? match[1] : '';

        const body = new URLSearchParams();
        if (csrfToken) body.set('csrf_token', csrfToken);
        body.set('email', email);
        body.set('password', password);

        return this.http.post(this.LOGIN_URL, body.toString(), {
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          observe: 'response',
          responseType: 'text'
        });
      }),
      switchMap(response => {
        if (response.url && response.url.includes('dashboard')) {
          return this.http.get<any>('/api/auth/me').pipe(
            tap(user => {
              localStorage.setItem('user', JSON.stringify(user));
              this.currentUserSubject.next(user);
            })
          );
        } else {
          throw new Error('Credenciales inválidas');
        }
      })
    );
  }

  logout(): Observable<any> {
    return this.http.get('/logout', { responseType: 'text' }).pipe(
      tap(() => {
        localStorage.removeItem('user');
        this.currentUserSubject.next(null);
      })
    );
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('user');
  }
}
