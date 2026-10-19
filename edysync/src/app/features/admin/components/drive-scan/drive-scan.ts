import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  HostListener,
  OnDestroy,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { DriveEntry, DriveService, ScanMode, ScannerStatus } from '../../../../core/services/drive';

interface PageView {
  n: number;
  url: string | null;
}

/** Escanear al drive: páginas del Epson L4150 (host) → PDF o JPG en la carpeta actual. */
@Component({
  selector: 'app-drive-scan',
  imports: [FormsModule, FontAwesomeModule],
  templateUrl: './drive-scan.html',
  styleUrl: './drive-scan.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DriveScan implements OnDestroy {
  private drive = inject(DriveService);
  private destroyRef = inject(DestroyRef);

  /** Carpeta del drive donde se guarda (ruta relativa; '' = Mi drive). */
  readonly folder = input('');
  readonly saved = output<DriveEntry>();
  readonly closed = output<void>();

  readonly qualities = [
    { value: 150, label: 'Borrador' },
    { value: 200, label: 'Normal' },
    { value: 300, label: 'Alta' },
  ];

  readonly status = signal<ScannerStatus | null>(null);
  readonly scanId = signal<string | null>(null);
  readonly pages = signal<PageView[]>([]);
  readonly scanning = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  resolution = 200;
  mode: ScanMode = 'Color';
  format: 'pdf' | 'jpg' = 'pdf';
  name = this.defaultName();

  readonly ready = computed(() => !!this.status()?.available);
  readonly folderLabel = computed(() => this.folder() || 'Mi drive');

  constructor() {
    this.drive
      .scanner()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (s) => this.status.set(s),
        error: () => this.status.set({ available: false, devices: [], help: 'No se pudo consultar el escáner.' }),
      });
  }

  @HostListener('document:keydown.escape')
  onEscape() {
    if (!this.scanning() && !this.saving()) this.cancel();
  }

  scan() {
    if (this.scanning() || !this.ready()) return;
    this.scanning.set(true);
    this.error.set(null);
    this.drive
      .scanPage({ scan_id: this.scanId() ?? undefined, resolution: this.resolution, mode: this.mode })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (draft) => {
          this.scanId.set(draft.scan_id);
          const known = new Map(this.pages().map((p) => [p.n, p]));
          this.pages.set(draft.pages.map((p) => known.get(p.n) ?? { n: p.n, url: null }));
          for (const p of this.pages()) if (!p.url) this.loadThumb(draft.scan_id, p.n);
          if (this.pages().length > 1) this.format = 'pdf';
          this.scanning.set(false);
        },
        error: (err) => {
          this.scanning.set(false);
          this.error.set(err?.error?.error || 'No se pudo escanear la página.');
        },
      });
  }

  private loadThumb(scanId: string, n: number) {
    this.drive
      .scanPageImage(scanId, n)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((blob) => {
        const url = URL.createObjectURL(blob);
        this.pages.update((list) => list.map((p) => (p.n === n ? { ...p, url } : p)));
      });
  }

  remove(page: PageView) {
    const id = this.scanId();
    if (!id) return;
    this.drive
      .removeScanPage(id, page.n)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          if (page.url) URL.revokeObjectURL(page.url);
          this.pages.update((list) => list.filter((p) => p.n !== page.n));
        },
        error: (err) => this.error.set(err?.error?.error || 'No se pudo quitar la página.'),
      });
  }

  save() {
    const id = this.scanId();
    if (!id || !this.pages().length || this.saving()) return;
    this.saving.set(true);
    this.error.set(null);
    this.drive
      .finishScan(id, { path: this.folder(), name: this.name.trim(), format: this.format })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (entry) => {
          this.saving.set(false);
          this.scanId.set(null);
          this.saved.emit(entry);
        },
        error: (err) => {
          this.saving.set(false);
          this.error.set(err?.error?.error || 'No se pudo guardar en el drive.');
        },
      });
  }

  cancel() {
    const id = this.scanId();
    if (id) this.drive.discardScan(id).subscribe({ error: () => undefined });
    this.scanId.set(null);
    this.closed.emit();
  }

  ngOnDestroy() {
    for (const p of this.pages()) if (p.url) URL.revokeObjectURL(p.url);
  }

  private defaultName() {
    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    return `Escaneo ${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}.${pad(d.getMinutes())}`;
  }
}
