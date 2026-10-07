import { Injectable, NgZone, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject, Subscription, interval, merge, fromEvent, of } from 'rxjs';
import { catchError, filter, map, startWith, switchMap } from 'rxjs/operators';

/**
 * Detecta cambios de configuración hechos en cualquier lugar (otra pestaña, otro administrador, el propio bot) y
 * avisa a la pantalla para que se recargue sola. Consulta `/api/live/versions` (una respuesta mínima) cada pocos
 * segundos mientras la pestaña está visible; al volver a la pestaña consulta de inmediato.
 */
@Injectable({ providedIn: 'root' })
export class LiveSyncService {
  private http = inject(HttpClient);
  private zone = inject(NgZone);

  /**
   * Emite el nombre de cada ámbito cuya versión cambió desde la última lectura (la primera lectura no emite).
   * `ping()` fuerza una consulta inmediata, p. ej. justo después de guardar.
   */
  watch(scopes: string[], periodMs = 4000): Observable<string> {
    return new Observable<string>((subscriber) => {
      const last = new Map<string, number>();
      const poke = new Subject<void>();
      const sub = new Subscription();

      const visible = () => typeof document === 'undefined' || document.visibilityState === 'visible';
      const triggers = merge(
        interval(periodMs).pipe(startWith(0)),
        poke,
        typeof document === 'undefined' ? of() : fromEvent(document, 'visibilitychange'),
      ).pipe(filter(() => visible()));

      this.zone.runOutsideAngular(() => {
        sub.add(
          triggers
            .pipe(
              switchMap(() =>
                this.http
                  .get<Record<string, number>>('/api/live/versions', { params: { scopes: scopes.join(',') } })
                  .pipe(catchError(() => of(null))),
              ),
              map((versions) => versions ?? {}),
            )
            .subscribe((versions) => {
              const changed: string[] = [];
              for (const [scope, version] of Object.entries(versions)) {
                if (last.has(scope) && last.get(scope) !== version) changed.push(scope);
                last.set(scope, version);
              }
              if (changed.length) this.zone.run(() => changed.forEach((s) => subscriber.next(s)));
            }),
        );
      });

      return () => sub.unsubscribe();
    });
  }
}
