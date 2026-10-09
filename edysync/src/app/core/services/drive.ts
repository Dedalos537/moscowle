import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, firstValueFrom } from 'rxjs';

export type DriveKind = 'folder' | 'image' | 'pdf' | 'word' | 'slides' | 'sheet' | 'archive' | 'audio' | 'video' | 'text' | 'file';

export interface DriveEntry {
  name: string;
  path: string;
  type: 'dir' | 'file';
  kind: DriveKind;
  size: number;
  modified: string;
  starred: boolean;
  items?: number;
}

export interface DriveUsage {
  used: number;
  quota: number;
  free: number;
}

export interface DriveListing {
  path?: string;
  entries: DriveEntry[];
  usage: DriveUsage;
}

export interface TrashEntry {
  id: string;
  name: string;
  original: string;
  deleted_at: string;
  type: 'dir' | 'file';
  kind: DriveKind;
  size: number;
}

export type DrivePreview =
  | { mode: 'image' | 'pdf' | 'audio' | 'video'; converted?: boolean }
  | { mode: 'html'; html: string }
  | { mode: 'slides'; slides: { title: string; blocks: string[][]; images: string[] }[] }
  | { mode: 'text'; text: string; truncated: boolean }
  | { mode: 'archive'; items: { name: string; size: number }[] }
  | { mode: 'none'; reason: string };

export interface Printer {
  name: string;
  state: 'idle' | 'printing' | 'disabled' | 'unknown';
  detail: string;
}

export interface PrinterStatus {
  available: boolean;
  printers: Printer[];
  default: string | null;
  help: string | null;
}

export interface PrintJob {
  id: number;
  file_path: string;
  file_name: string;
  printer: string;
  copies: number;
  duplex: boolean;
  color: boolean;
  page_range: string | null;
  scheduled_at: string | null;
  status: 'scheduled' | 'sent' | 'failed' | 'cancelled';
  error: string | null;
  created_at: string;
  sent_at: string | null;
}

export interface PrintOptions {
  path: string;
  printer: string;
  copies: number;
  duplex: boolean;
  color: boolean;
  page_range?: string;
  scheduled_at?: string | null;
}

/** API del drive del administrador. Los archivos se piden como Blob para que viajen con el token. */
@Injectable({ providedIn: 'root' })
export class DriveService {
  private http = inject(HttpClient);
  private readonly base = '/api/drive';

  list(path: string): Observable<DriveListing> {
    return this.http.get<DriveListing>(`${this.base}/list`, { params: new HttpParams().set('path', path) });
  }

  search(q: string): Observable<DriveListing> {
    return this.http.get<DriveListing>(`${this.base}/search`, { params: new HttpParams().set('q', q) });
  }

  recent(): Observable<DriveListing> {
    return this.http.get<DriveListing>(`${this.base}/recent`);
  }

  starred(): Observable<DriveListing> {
    return this.http.get<DriveListing>(`${this.base}/starred`);
  }

  setStarred(paths: string[], starred: boolean): Observable<DriveListing> {
    return this.http.post<DriveListing>(`${this.base}/starred`, { paths, starred });
  }

  mkdir(path: string, name: string): Observable<DriveEntry> {
    return this.http.post<DriveEntry>(`${this.base}/folder`, { path, name });
  }

  rename(path: string, name: string): Observable<DriveEntry> {
    return this.http.post<DriveEntry>(`${this.base}/rename`, { path, name });
  }

  move(paths: string[], dest: string): Observable<{ entries: DriveEntry[] }> {
    return this.http.post<{ entries: DriveEntry[] }>(`${this.base}/move`, { paths, dest });
  }

  copy(paths: string[], dest: string): Observable<{ entries: DriveEntry[] }> {
    return this.http.post<{ entries: DriveEntry[] }>(`${this.base}/copy`, { paths, dest });
  }

  trash(paths: string[]): Observable<{ trashed: number }> {
    return this.http.post<{ trashed: number }>(`${this.base}/delete`, { paths });
  }

  compress(paths: string[], dest: string, name: string): Observable<DriveEntry> {
    return this.http.post<DriveEntry>(`${this.base}/compress`, { paths, dest, name });
  }

  extract(path: string): Observable<DriveEntry> {
    return this.http.post<DriveEntry>(`${this.base}/extract`, { path });
  }

  trashList(): Observable<{ entries: TrashEntry[]; usage: DriveUsage }> {
    return this.http.get<{ entries: TrashEntry[]; usage: DriveUsage }>(`${this.base}/trash`);
  }

  restore(ids: string[]): Observable<{ restored: number }> {
    return this.http.post<{ restored: number }>(`${this.base}/trash/restore`, { ids });
  }

  emptyTrash(ids?: string[]): Observable<{ purged: number }> {
    return this.http.post<{ purged: number }>(`${this.base}/trash/empty`, ids ? { ids } : {});
  }

  preview(path: string): Observable<DrivePreview> {
    return this.http.get<DrivePreview>(`${this.base}/preview`, { params: new HttpParams().set('path', path) });
  }

  /** Contenido como Blob (con el token): imágenes, PDF y descargas. */
  blob(path: string, kind: 'file' | 'thumb' | 'pdf' = 'file'): Observable<Blob> {
    const url = kind === 'thumb' ? 'thumb' : kind === 'pdf' ? 'preview/pdf' : 'file';
    let params = new HttpParams().set('path', path);
    if (kind === 'file') params = params.set('inline', '1');
    return this.http.get(`${this.base}/${url}`, { params, responseType: 'blob' });
  }

  printers(): Observable<PrinterStatus> {
    return this.http.get<PrinterStatus>(`${this.base}/printers`);
  }

  print(options: PrintOptions): Observable<PrintJob> {
    return this.http.post<PrintJob>(`${this.base}/print`, options);
  }

  printJobs(): Observable<{ jobs: PrintJob[] }> {
    return this.http.get<{ jobs: PrintJob[] }>(`${this.base}/print/jobs`);
  }

  cancelPrint(id: number): Observable<PrintJob> {
    return this.http.post<PrintJob>(`${this.base}/print/jobs/${id}/cancel`, {});
  }

  /**
   * Sube un archivo en partes de 8 MB (Cloudflare corta cuerpos grandes). `onProgress` recibe bytes enviados.
   * `name` puede traer subcarpetas («fotos/2026/a.jpg») cuando se arrastra una carpeta completa.
   */
  async upload(folder: string, file: File, name: string, onProgress: (sent: number) => void, signal: AbortSignal): Promise<DriveEntry> {
    const init = await firstValueFrom(
      this.http.post<{ upload_id: string; chunk_size: number }>(`${this.base}/upload/init`, { path: folder, name, size: file.size }),
    );
    const id = init.upload_id;
    try {
      let offset = 0;
      while (offset < file.size) {
        if (signal.aborted) throw new DOMException('Cancelado', 'AbortError');
        const part = file.slice(offset, offset + init.chunk_size);
        const res = await firstValueFrom(
          this.http.put<{ received: number }>(`${this.base}/upload/${id}`, part, {
            params: new HttpParams().set('offset', offset),
            headers: { 'Content-Type': 'application/octet-stream' },
          }),
        );
        offset = res.received;
        onProgress(offset);
      }
      return await firstValueFrom(this.http.post<DriveEntry>(`${this.base}/upload/${id}/complete`, {}));
    } catch (err) {
      this.http.delete(`${this.base}/upload/${id}`).subscribe({ error: () => undefined });
      throw err;
    }
  }
}
