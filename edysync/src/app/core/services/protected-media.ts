import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, from, of } from 'rxjs';

/**
 * Archivos protegidos (adjuntos del chat) cargados con el token y desde la API.
 *
 * `<img src="/uploads/...">` no servía en producción: desde el dominio del cPanel la ruta relativa apunta al hosting y
 * no a la API, y Safari (iPhone) bloquea la cookie de terceros con la que viajaba la sesión. Aquí se piden con
 * HttpClient (los interceptores ponen la base de la API y el token) y se entregan como URL local del navegador.
 */
@Injectable({ providedIn: 'root' })
export class ProtectedMedia {
  private http = inject(HttpClient);
  private cache = new Map<string, Promise<string>>();
  private readonly limit = 120;

  /** URL local (blob:) del archivo. Las URLs blob:/data: ya locales se devuelven tal cual. */
  url(src: string | null | undefined): Promise<string | null> {
    if (!src) return Promise.resolve(null);
    if (src.startsWith('blob:') || src.startsWith('data:')) return Promise.resolve(src);
    let hit = this.cache.get(src);
    if (!hit) {
      hit = new Promise<string>((resolve, reject) => {
        this.http.get(src, { responseType: 'blob' }).subscribe({
          next: (blob) => resolve(URL.createObjectURL(blob)),
          error: (err) => {
            this.cache.delete(src);
            reject(err);
          },
        });
      });
      this.cache.set(src, hit);
      this.trim();
    }
    return hit;
  }

  url$(src: string | null | undefined): Observable<string | null> {
    if (!src) return of(null);
    return from(this.url(src).catch(() => null));
  }

  /** Descarga con el nombre original. */
  async download(src: string, name: string) {
    const url = await this.url(src);
    if (!url) return;
    const a = document.createElement('a');
    a.href = url;
    a.download = name || 'archivo';
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  /** Abre en otra pestaña. La pestaña se abre ANTES de esperar la descarga para que el navegador no la bloquee. */
  async open(src: string) {
    const tab = window.open('', '_blank');
    try {
      const url = await this.url(src);
      if (url && tab) tab.location.href = url;
      else tab?.close();
    } catch {
      tab?.close();
    }
  }

  private trim() {
    while (this.cache.size > this.limit) {
      const oldest = this.cache.keys().next().value as string;
      this.cache.get(oldest)?.then((u) => URL.revokeObjectURL(u)).catch(() => undefined);
      this.cache.delete(oldest);
    }
  }
}
