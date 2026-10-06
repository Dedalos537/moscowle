import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError, map, shareReplay } from 'rxjs/operators';

/**
 * Las fotos de perfil requieren sesión, así que no pueden ir en un <img src> directo (no envía el token).
 * Se descargan con HttpClient como blob y se reutilizan por URL (la URL lleva ?v=<mtime>, así que cambia al cambiar la foto).
 */
@Injectable({ providedIn: 'root' })
export class AvatarService {
  private cache = new Map<string, Observable<string | null>>();

  constructor(private http: HttpClient) {}

  blobUrl(avatar: string | null | undefined): Observable<string | null> {
    if (!avatar) return of(null);
    let req = this.cache.get(avatar);
    if (!req) {
      req = this.http.get(avatar, { responseType: 'blob' }).pipe(
        map((blob) => URL.createObjectURL(blob)),
        catchError(() => of(null)),
        shareReplay(1),
      );
      this.cache.set(avatar, req);
    }
    return req;
  }
}
