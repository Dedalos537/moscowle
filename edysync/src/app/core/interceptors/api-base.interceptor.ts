import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

@Injectable()
export class ApiBaseInterceptor implements HttpInterceptor {
  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const base = environment.apiBaseUrl;
    if (base && req.url.startsWith('/')) {
      const newReq = req.clone({ url: base + req.url });
      return next.handle(newReq);
    }
    return next.handle(req);
  }
}
