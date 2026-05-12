import { Injectable, NgZone } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable, from } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

@Injectable()
export class ApiBaseInterceptor implements HttpInterceptor {
  constructor(private ngZone: NgZone) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return from(this.generateAppKey()).pipe(
      switchMap(appKey => {
        let headers = req.headers.set('X-App-Key', appKey);
        let url = req.url;
        
        const base = environment.apiBaseUrl;
        if (base && url.startsWith('/')) {
          url = base + url;
        }

        const newReq = req.clone({ url, headers });
        
        return new Observable<HttpEvent<any>>(observer => {
          const sub = next.handle(newReq).subscribe({
            next: (event) => this.ngZone.run(() => observer.next(event)),
            error: (err) => this.ngZone.run(() => observer.error(err)),
            complete: () => this.ngZone.run(() => observer.complete())
          });
          return () => sub.unsubscribe();
        });
      })
    );
  }

  private async generateAppKey(): Promise<string> {
    const secret = 'EdySync_Mvp_Secret_2026';
    // Using 5-minute windows (300 seconds) for basic synchronization tolerance
    const timestamp = Math.floor(Date.now() / 1000 / 300); 
    const message = `${secret}:${timestamp}`;
    const msgBuffer = new TextEncoder().encode(message);
    const hashBuffer = await crypto.subtle.digest('SHA-256', msgBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return `${timestamp}.${hashHex}`;
  }
}
