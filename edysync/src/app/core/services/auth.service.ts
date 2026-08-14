import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap, of, timeout, catchError } from 'rxjs';
import { DataCacheService } from './cache.service';
import { PreloadService } from './preload.service';

export interface LoginResponse {
  valid?: boolean;
  user?: any;
}

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private readonly LOGIN_URL = '/api/login';
  private readonly ME_URL = '/api/auth/me';

  private currentUserSubject = new BehaviorSubject<any>(null);
  public currentUser$ = this.currentUserSubject.asObservable();

  constructor(
    private http: HttpClient,
    private cache: DataCacheService,
    private preload: PreloadService,
  ) {
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      this.currentUserSubject.next(JSON.parse(storedUser));
    }
  }

  verifySession(): Observable<any> {
    return this.http.get<any>(this.ME_URL).pipe(
      timeout(15000),
      tap(res => {
        if (res.id) {
          localStorage.setItem('user', JSON.stringify(res));
          this.currentUserSubject.next(res);
          this.preload.preloadFor(res.role);
        } else {
          localStorage.removeItem('user');
          this.currentUserSubject.next(null);
        }
      })
    );
  }

  login(email: string, password: string): Observable<any> {
    return this.http.post<any>(this.LOGIN_URL, { email, password }).pipe(
      timeout(60000),
      catchError(err => {
        if (err.name === 'TimeoutError') {
          throw { error: { message: 'El servidor tardó demasiado en responder. Intenta de nuevo.' } };
        }
        throw err;
      }),
      tap(res => {
        if (res.success) {
          localStorage.setItem('user', JSON.stringify(res.user));
          if (res.csrf_token) {
            localStorage.setItem('csrf_token', res.csrf_token);
          }
          if (res.access_token) {
            localStorage.setItem('access_token', res.access_token);
          }
          this.currentUserSubject.next(res.user);
          this.preload.preloadFor(res.user?.role);
        }
      })
    );
  }

  logout(): Observable<any> {
    return this.http.post('/api/logout', {}).pipe(
      tap(() => {
        localStorage.removeItem('user');
        localStorage.removeItem('csrf_token');
        localStorage.removeItem('access_token');
        this.cache.clear();
        this.currentUserSubject.next(null);
      })
    );
  }

  clearSession(): void {
    localStorage.removeItem('user');
    localStorage.removeItem('csrf_token');
    localStorage.removeItem('access_token');
    this.cache.clear();
    this.currentUserSubject.next(null);
  }

  isLoggedIn(): boolean {
    return !!localStorage.getItem('user');
  }
}
