import { Injectable, NgZone } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

let cachedAppKey: string | null = null;
let cachedAppKeyExpiry = 0;

@Injectable()
export class ApiBaseInterceptor implements HttpInterceptor {
  constructor(private ngZone: NgZone) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const skipAppKey = req.url.includes('/api/public/')
      || req.url.includes('/api/health');

    if (skipAppKey) {
      return this.proceed(req, next, null);
    }

    return from(this.getAppKey()).pipe(
      switchMap(appKey => this.proceed(req, next, appKey))
    );
  }

  private proceed(req: HttpRequest<any>, next: HttpHandler, appKey: string | null): Observable<HttpEvent<any>> {
    let headers = appKey ? req.headers.set('X-App-Key', appKey) : req.headers;
    let url = req.url;

    const base = environment.apiBaseUrl;
    if (base && url.startsWith('/')) {
      url = base + url;
    }

    const newReq = req.clone({ url, headers, withCredentials: true });

    return new Observable<HttpEvent<any>>(observer => {
      const sub = next.handle(newReq).subscribe({
        next: (event) => this.ngZone.run(() => observer.next(event)),
        error: (err) => this.ngZone.run(() => observer.error(err)),
        complete: () => this.ngZone.run(() => observer.complete())
      });
      return () => sub.unsubscribe();
    });
  }

  private async getAppKey(): Promise<string | null> {
    const now = Math.floor(Date.now() / 1000);
    if (cachedAppKey && now < cachedAppKeyExpiry) {
      return cachedAppKey;
    }
    try {
      const base = environment.apiBaseUrl || '';
      const res = await fetch(`${base}/api/public/app-key`);
      const data = await res.json();
      cachedAppKey = data.app_key;
      cachedAppKeyExpiry = now + data.expires_in - 10;
      return data.app_key;
    } catch {
      return null;
    }
  }
}
