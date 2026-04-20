import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor
} from '@angular/common/http';
import { Observable } from 'rxjs';
import { AuthService } from '../services/auth.service';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private authService: AuthService) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    // Al usar flask-login (cookies de sesión), indicamos que el navegador 
    // siempre envíe la cookie en peticiones cross-origin hacia el backend
    request = request.clone({ 
      withCredentials: true 
    });

    return next.handle(request);
  }
}
