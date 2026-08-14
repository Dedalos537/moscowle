import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpResponse, HttpErrorResponse } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { tap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { DataCacheService } from '../services/cache.service';

const DEFAULT_TTL_MS = 5 * 60 * 1000;

const EXCLUDED = [
  '/api/health',
  '/api/public/',
  '/api/time',
  '/api/auth/me',
  '/api/logout',
  '/api/login',
  '/api/sessions/current'
];

const SHORT_TTL_MS = 30 * 1000;

const SHORT_TTL_PATTERNS = [
  '/dashboard',
  '/dashboard-stats',
  '/admin/api/overview',
  '/api/incidents/dashboard',
  '/api/incidents',
  '/admin/api/financial-summary',
  '/admin/api/contracts/monthly-breakdown',
  '/api/sessions/',
  '/api/notifications',
  '/api/messages/unread-count'
];

const LONG_TTL_MS = 30 * 60 * 1000;

const LONG_TTL_PATTERNS = [
  '/api/patients',
  '/api/games',
  '/api/admin/sedes',
  '/therapist/api/profile',
  '/patient/api/my-therapist',
  '/api/admin/contracts'
];

const ID_ACTION_RE = /\/(\d+)(\/.*)?$/;

@Injectable()
export class CacheInterceptor implements HttpInterceptor {
  constructor(private cache: DataCacheService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const method = req.method.toUpperCase();

    if (method !== 'GET') {
      this.invalidateOnMutation(method, req.url);
      return next.handle(req);
    }

    if (!this.isCacheable(req)) {
      return next.handle(req);
    }

    const key = this.normalizeKey(req.urlWithParams);
    const cached = this.cache.get<any>(key);

    if (cached !== null && cached !== undefined) {
      return of(new HttpResponse({ status: 200, body: cached, url: req.url }));
    }

    return next.handle(req).pipe(
      tap(event => {
        if (event instanceof HttpResponse && event.status === 200 && event.body !== null && event.body !== undefined) {
          this.cache.set(key, event.body, this.ttlFor(req.url));
        }
      })
    );
  }

  private isCacheable(req: HttpRequest<any>): boolean {
    if (req.responseType && req.responseType !== 'json') {
      return false;
    }
    const url = this.normalizeUrl(req.url);
    return !EXCLUDED.some(e => url.includes(e));
  }

  private normalizeKey(urlWithParams: string): string {
    const url = this.normalizeUrl(urlWithParams);
    const qIndex = url.indexOf('?');
    if (qIndex === -1) {
      return url;
    }
    const path = url.slice(0, qIndex);
    const params = url.slice(qIndex + 1).split('&').sort();
    return path + '?' + params.join('&');
  }

  private normalizeUrl(url: string): string {
    let clean = url;
    const base = environment.apiBaseUrl;
    if (base && clean.startsWith(base)) {
      clean = clean.slice(base.length);
    }
    return clean || '/';
  }

  private ttlFor(url: string): number {
    const clean = this.normalizeUrl(url);
    if (LONG_TTL_PATTERNS.some(p => clean.includes(p))) {
      return LONG_TTL_MS;
    }
    if (SHORT_TTL_PATTERNS.some(p => clean.includes(p))) {
      return SHORT_TTL_MS;
    }
    return DEFAULT_TTL_MS;
  }

  private invalidateOnMutation(method: string, url: string): void {
    if (method === 'POST' && url.includes('/api/logout')) {
      this.cache.clear();
      return;
    }

    const clean = this.normalizeUrl(url);
    const noQuery = clean.split('?')[0];

    if (noQuery.includes('/api/admin/')) {
      this.cache.invalidateContaining('/api/admin');
      this.cache.invalidateContaining('/admin/api');
    }

    const root = this.resourceRoot(noQuery);
    if (root) {
      this.cache.invalidateContaining(root);
    }
  }

  private resourceRoot(url: string): string | null {
    const segments = url.split('/').filter(Boolean);
    if (segments.length === 0) {
      return null;
    }
    const path = '/' + segments.join('/');
    const match = path.match(ID_ACTION_RE);
    if (match && match[1]) {
      return path.slice(0, match.index!);
    }
    return path;
  }
}
