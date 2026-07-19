import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse,
  HttpClient
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, switchMap } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

let isRefreshing = false;
let pendingRequests: Array<{ resolve: (value: boolean) => void }> = [];

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
  return match ? decodeURIComponent(match[2]) : null;
}

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(
    private authService: AuthService,
    private router: Router,
    private http: HttpClient,
  ) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const csrfToken = getCookie('csrf_token') || localStorage.getItem('csrf_token');
    const accessToken = localStorage.getItem('access_token');

    let headers: Record<string, string> = {};

    if (csrfToken && !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(request.method)) {
      headers['X-CSRFToken'] = csrfToken;
    }

    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    request = request.clone({ setHeaders: headers, withCredentials: true });

    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401 && !request.url.includes('/api/auth/refresh')) {
          return this.handle401(request, next);
        }
        return throwError(() => error);
      })
    );
  }

  private handle401(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    if (!isRefreshing) {
      isRefreshing = true;

      return this.http.post('/api/auth/refresh', {}, { withCredentials: true }).pipe(
        switchMap((res: any) => {
          isRefreshing = false;
          if (res?.access_token) {
            localStorage.setItem('access_token', res.access_token);
          }
          pendingRequests.forEach(p => p.resolve(true));
          pendingRequests = [];
          return next.handle(request);
        }),
        catchError((refreshError) => {
          isRefreshing = false;
          pendingRequests.forEach(p => p.resolve(false));
          pendingRequests = [];
          this.authService.clearSession();
          this.router.navigate(['/auth/login']);
          return throwError(() => refreshError);
        }),
      );
    }

    return new Observable<HttpEvent<unknown>>(observer => {
      pendingRequests.push({
        resolve: (success: boolean) => {
          if (success) {
            next.handle(request).subscribe({
              next: e => observer.next(e),
              error: e => observer.error(e),
              complete: () => observer.complete(),
            });
          } else {
            observer.error(request as any);
          }
        },
      });
    });
  }
}
