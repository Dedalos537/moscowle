import { Pipe, PipeTransform, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { ProtectedMedia } from '../../core/services/protected-media';

/** `[src]="msg.file_url | authMedia | async"`: carga el archivo con el token y devuelve una URL local. */
@Pipe({ name: 'authMedia', standalone: true })
export class AuthMediaPipe implements PipeTransform {
  private media = inject(ProtectedMedia);

  transform(src: string | null | undefined): Observable<string | null> {
    return this.media.url$(src);
  }
}
