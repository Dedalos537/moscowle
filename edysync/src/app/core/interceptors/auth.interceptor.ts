// DCE — Diego Centeno Estuvo Acá
import { Injectable } from '@angular/core';
import {
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpInterceptor,
  HttpErrorResponse
} from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthService } from '../services/auth.service';
import { Router } from '@angular/router';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private authService: AuthService, private router: Router) {}

  intercept(request: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    const csrfToken = localStorage.getItem('csrf_token');
    
    // Configurar peticiones para llevar la cookie de sesión de flask
    let reqConfig: any = {
      withCredentials: true
    };

    // Agregar el token CSRF a los headers en peticiones de modificación
    if (csrfToken && !['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(request.method)) {
      reqConfig.setHeaders = {
        'X-CSRFToken': csrfToken
      };
    }

    request = request.clone(reqConfig);

    return next.handle(request).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error.status === 401) {
          // Sesión expirada o no iniciada
          this.router.navigate(['/auth/login']);
        }
        return throwError(() => error);
      })
    );
  }
}
