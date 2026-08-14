import { Injectable, NgZone } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ToastService } from '../services/toast.service';
import { SILENT_HTTP } from '../services/preload.service';

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  constructor(
    private toastService: ToastService,
    private ngZone: NgZone,
  ) {}

  intercept(req: HttpRequest<unknown>, next: HttpHandler): Observable<HttpEvent<unknown>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        if (req.context.get(SILENT_HTTP)) {
          return throwError(() => error);
        }
        this.ngZone.run(() => {
          if (error.status === 0) {
            this.toastService.show('Error de conexión — verifica que el servidor esté disponible', 'error');
          } else if (error.status === 401) {
            return;
          } else if (error.status === 403) {
            this.toastService.show('No tienes permiso para realizar esta acción', 'warning');
          } else if (error.status === 404) {
            if (!req.url.includes('/api/search') && !req.url.includes('/api/v1/search')) {
              this.toastService.show(`Recurso no encontrado: ${req.url}`, 'warning');
            }
          } else if (error.status >= 500) {
            this.toastService.show('Error del servidor — intenta nuevamente', 'error');
          } else if (error.error?.error || error.error?.message) {
            this.toastService.show(error.error.error || error.error.message, 'error');
          } else {
            this.toastService.show(`Error ${error.status} al cargar datos`, 'error');
          }
        });
        return throwError(() => error);
      }),
    );
  }
}
