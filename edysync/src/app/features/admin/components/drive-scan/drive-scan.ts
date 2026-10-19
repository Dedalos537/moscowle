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
import { firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { DriveEntry, DriveService, ScanMode, ScanSize, ScannerStatus } from '../../../../core/services/drive';

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
  private confirm = inject(ConfirmService);
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

  /** Tamaños que caben en el vidrio de la L4150 (máx. 216 × 297 mm). */
  readonly sizes: { value: ScanSize; label: string; hint: string }[] = [
    { value: 'A4', label: 'A4', hint: '210 × 297 mm' },
    { value: 'Carta', label: 'Carta', hint: '216 × 279 mm' },
    { value: 'Oficio', label: 'Oficio', hint: 'hasta 297 mm de largo (lo que cabe en el vidrio)' },
    { value: 'B5', label: 'B5', hint: '176 × 250 mm' },
    { value: 'A5', label: 'A5', hint: '148 × 210 mm' },
    { value: 'A6', label: 'A6', hint: '105 × 148 mm' },
    { value: 'full', label: 'Todo el vidrio', hint: 'área completa del escáner' },
  ];

  readonly status = signal<ScannerStatus | null>(null);
  /** Página abierta en grande (índice en `pages`), o null. */
  readonly preview = signal<number | null>(null);
  private asking = false;
  readonly scanId = signal<string | null>(null);
  readonly pages = signal<PageView[]>([]);
  readonly scanning = signal(false);
  readonly saving = signal(false);
  readonly error = signal<string | null>(null);

  resolution = 200;
  mode: ScanMode = 'Color';
  size: ScanSize = 'A4';
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

  /** Escape cierra primero la vista grande; el panel solo se cierra solo si no hay páginas sin guardar. */
  @HostListener('document:keydown.escape')
  onEscape() {
    if (this.preview() !== null) {
      this.preview.set(null);
      return;
    }
    if (!this.pages().length && !this.scanning() && !this.saving() && !this.asking) this.closed.emit();
  }

  @HostListener('document:keydown.arrowright')
  next() {
    this.step(1);
  }

  @HostListener('document:keydown.arrowleft')
  prev() {
    this.step(-1);
  }

  private step(dir: number) {
    const i = this.preview();
    if (i === null) return;
    const n = this.pages().length;
    this.preview.set((i + dir + n) % n);
  }

  open(i: number) {
    this.preview.set(i);
  }

  sizeHint(): string {
    return this.sizes.find((s) => s.value === this.size)?.hint ?? '';
  }

  scan() {
    if (this.scanning() || !this.ready()) return;
    this.scanning.set(true);
    this.error.set(null);
    this.drive
      .scanPage({ scan_id: this.scanId() ?? undefined, resolution: this.resolution, mode: this.mode, size: this.size })
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
          const i = this.preview();
          if (i !== null) this.preview.set(this.pages().length ? Math.min(i, this.pages().length - 1) : null);
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

  /** Cerrar sin guardar: si hay páginas escaneadas se pregunta antes (antes se perdían con un clic fuera). */
  async cancel() {
    if (this.saving() || this.asking) return;
    const id = this.scanId();
    if (id && this.pages().length) {
      this.asking = true;
      const ok = await firstValueFrom(
        this.confirm.confirm({
          title: 'Descartar el escaneo',
          message: `Se perderán ${this.pages().length === 1 ? 'la página escaneada' : `las ${this.pages().length} páginas escaneadas`}.`,
          confirmText: 'Descartar',
          cancelText: 'Seguir escaneando',
          variant: 'danger',
        }),
      );
      this.asking = false;
      if (!ok) return;
    }
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
