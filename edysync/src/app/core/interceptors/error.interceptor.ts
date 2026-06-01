import { Injectable, NgZone } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AlertService } from '../services/alert.service';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  constructor(
    private alertService: AlertService,
    private ngZone: NgZone,
  ) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        this.ngZone.run(() => {
          if (error.status === 0) {
            this.alertService.show('Error de conexión — verifica que el servidor esté disponible', 'error');
          } else if (error.status === 401) {
            return;
          } else if (error.status === 403) {
            this.alertService.show('No tienes permiso para realizar esta acción', 'warning');
          } else if (error.status === 404) {
            if (!req.url.includes('/api/search') && !req.url.includes('/api/v1/search')) {
              this.alertService.show(`Recurso no encontrado: ${req.url}`, 'warning');
            }
          } else if (error.status >= 500) {
            this.alertService.show('Error del servidor — intenta nuevamente', 'error');
          } else if (error.error?.error || error.error?.message) {
            this.alertService.show(error.error.error || error.error.message, 'error');
          } else {
            this.alertService.show(`Error ${error.status} al cargar datos`, 'error');
          }
        });
        return throwError(() => error);
      }),
    );
  }
}
