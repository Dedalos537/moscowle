import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import { Subscription, finalize, firstValueFrom } from 'rxjs';
import {
  DriveEntry,
  DriveKind,
  DrivePreview,
  DriveService,
  DriveUsage,
  PrintJob,
  PrinterStatus,
  TrashEntry,
} from '../../../../core/services/drive';
import { AuthService } from '../../../../core/services/auth.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { HeaderService } from '../../../../core/services/header.service';
import { ToastService } from '../../../../core/services/toast.service';

type Place = 'files' | 'recent' | 'starred' | 'trash' | 'prints';
type SortKey = 'name' | 'size' | 'modified';

interface UploadOp {
  id: number;
  name: string;
  size: number;
  sent: number;
  state: 'running' | 'done' | 'error' | 'cancelled';
  error?: string;
  ctrl: AbortController;
  /** Subidas muestran porcentaje; comprimir, extraer, mover y copiar, una barra indeterminada. */
  kind?: 'upload' | 'compress' | 'extract' | 'move' | 'copy';
}

const LEAVE_MS = 200;

interface MenuState {
  x: number;
  y: number;
  target: DriveEntry | null; // null = fondo de la carpeta
}

const ICONS: Record<DriveKind, IconProp> = {
  folder: ['fas', 'folder'],
  image: ['fas', 'file-image'],
  pdf: ['fas', 'file-pdf'],
  word: ['fas', 'file-word'],
  slides: ['fas', 'file-powerpoint'],
  sheet: ['fas', 'file-excel'],
  archive: ['fas', 'file-zipper'],
  audio: ['fas', 'file-audio'],
  video: ['fas', 'file-video'],
  text: ['fas', 'file-lines'],
  file: ['fas', 'file'],
};

const PRINTABLE: DriveKind[] = ['pdf', 'image', 'text', 'word', 'slides', 'sheet'];

/**
 * Drive del administrador, al estilo de Archivos de GNOME: lugares a la izquierda, barra de ruta, cuadrícula o lista,
 * selección con clic/Mayús/Ctrl, menú contextual, atajos de teclado, arrastrar y soltar (archivos y carpetas enteras),
 * vista rápida con flechas, operaciones en curso y diálogo de impresión con programación.
 */
@Component({
  selector: 'app-drive',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule],
  templateUrl: './drive.html',
  styleUrl: './drive.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Drive implements OnInit, OnDestroy {
  private api = inject(DriveService);
  private auth = inject(AuthService);
  private confirm = inject(ConfirmService);
  private header = inject(HeaderService);
  private toast = inject(ToastService);
  private sanitizer = inject(DomSanitizer);
  private subs = new Subscription();

  @ViewChild('searchInput') searchInput?: ElementRef<HTMLInputElement>;
  @ViewChild('renameInput') renameInput?: ElementRef<HTMLInputElement>;
  @ViewChild('fileInput') fileInput?: ElementRef<HTMLInputElement>;

  /** La raíz como destino de arrastre (lugar «Inicio» y primer botón de la ruta). */
  readonly home: DriveEntry = { name: 'Inicio', path: '', type: 'dir', kind: 'folder', size: 0, modified: '', starred: false };
  readonly isAdmin = signal(true);
  readonly place = signal<Place>('files');
  readonly path = signal('');
  readonly entries = signal<DriveEntry[]>([]);
  readonly trashEntries = signal<TrashEntry[]>([]);
  readonly usage = signal<DriveUsage | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly view = signal<'grid' | 'list'>(this.readPref('drive.view', 'grid') as 'grid' | 'list');
  readonly sort = signal<{ key: SortKey; dir: 1 | -1 }>({ key: 'name', dir: 1 });
  readonly query = signal('');
  readonly selected = signal<Set<string>>(new Set());
  readonly clipboard = signal<{ mode: 'copy' | 'cut'; paths: string[] } | null>(null);
  readonly menu = signal<MenuState | null>(null);
  readonly renaming = signal<string | null>(null);
  readonly creatingFolder = signal(false);
  readonly dropActive = signal(false);
  readonly dropTarget = signal<string | null>(null);
  readonly uploads = signal<UploadOp[]>([]);
  readonly thumbs = signal<Record<string, string>>({});
  /** Elementos que se están yendo (animación de salida) y los recién llegados (entrada + resaltado). */
  readonly leaving = signal<Set<string>>(new Set());
  readonly fresh = signal<Set<string>>(new Set());
  private freshTimer: ReturnType<typeof setTimeout> | null = null;
  renameDraft = '';
  folderDraft = '';
  private anchor = -1;
  private searchTimer: ReturnType<typeof setTimeout> | null = null;
  private uploadSeq = 0;
  private thumbQueue: string[] = [];
  private thumbActive = 0;
  private dragPaths: string[] = [];

  // Vista rápida
  readonly previewEntry = signal<DriveEntry | null>(null);
  readonly preview = signal<DrivePreview | null>(null);
  readonly previewUrl = signal<string | null>(null);
  readonly previewSafeUrl = signal<SafeResourceUrl | null>(null);
  readonly previewLoading = signal(false);

  // Impresión
  readonly printEntry = signal<DriveEntry | null>(null);
  readonly printers = signal<PrinterStatus | null>(null);
  readonly printJobs = signal<PrintJob[]>([]);
  readonly printing = signal(false);
  printForm = { printer: '', copies: 1, duplex: false, color: true, page_range: '', when: 'now' as 'now' | 'later', at: '' };

  readonly crumbs = computed(() => {
    const parts = this.path() ? this.path().split('/') : [];
    return parts.map((name, i) => ({ name, path: parts.slice(0, i + 1).join('/') }));
  });

  readonly visible = computed(() => {
    const { key, dir } = this.sort();
    const list = [...this.entries()];
    list.sort((a, b) => {
      if (a.type !== b.type) return a.type === 'dir' ? -1 : 1;
      if (key === 'size') return (a.size - b.size) * dir;
      if (key === 'modified') return (Date.parse(a.modified) - Date.parse(b.modified)) * dir;
      return a.name.localeCompare(b.name, 'es', { numeric: true, sensitivity: 'base' }) * dir;
    });
    return list;
  });

  readonly selectedEntries = computed(() => this.visible().filter((e) => this.selected().has(e.path)));
  readonly usagePct = computed(() => {
    const u = this.usage();
    return u ? Math.min(100, Math.round((u.used / u.quota) * 1000) / 10) : 0;
  });
  readonly activeUploads = computed(() => this.uploads().filter((u) => u.state === 'running').length);

  readonly places: { id: Place; label: string; icon: IconProp }[] = [
    { id: 'files', label: 'Inicio', icon: ['fas', 'house'] },
    { id: 'recent', label: 'Recientes', icon: ['fas', 'clock-rotate-left'] },
    { id: 'starred', label: 'Destacados', icon: ['fas', 'star'] },
    { id: 'trash', label: 'Papelera', icon: ['fas', 'trash-can'] },
    { id: 'prints', label: 'Impresiones', icon: ['fas', 'print'] },
  ];

  ngOnInit() {
    this.header.setConfig({ title: 'Drive', subtitle: 'Archivos del centro e impresión', icon: ['fas', 'hard-drive'] });
    this.subs.add(
      this.auth.currentUser$.subscribe((u: { role?: string } | null) => {
        this.isAdmin.set(!u || u.role === 'admin');
      }),
    );
    this.load();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
    this.header.reset();
    Object.values(this.thumbs()).forEach((u) => URL.revokeObjectURL(u));
    this.closePreview();
    this.uploads().forEach((u) => u.state === 'running' && u.ctrl.abort());
  }

  // ── navegación ─────────────────────────────────────────────────────────────
  go(place: Place, path = '') {
    this.place.set(place);
    this.path.set(path);
    this.query.set('');
    this.clearSelection();
    this.menu.set(null);
    this.renaming.set(null);
    this.creatingFolder.set(false);
    this.load();
  }

  open(entry: DriveEntry) {
    if (entry.type === 'dir') this.go('files', entry.path);
    else this.openPreview(entry);
  }

  up() {
    if (this.place() !== 'files' || !this.path()) return;
    const parts = this.path().split('/');
    parts.pop();
    this.go('files', parts.join('/'));
  }

  load() {
    this.loading.set(true);
    this.error.set(null);
    const place = this.place();
    if (place === 'trash') {
      this.api.trashList().subscribe({
        next: (r) => {
          this.trashEntries.set(r.entries);
          this.usage.set(r.usage);
          this.loading.set(false);
        },
        error: (e) => this.fail(e),
      });
      return;
    }
    if (place === 'prints') {
      this.loadPrinters();
      this.api.printJobs().subscribe({
        next: (r) => {
          this.printJobs.set(r.jobs);
          this.loading.set(false);
        },
        error: (e) => this.fail(e),
      });
      return;
    }
    const q = this.query().trim();
    const req =
      q.length >= 2 ? this.api.search(q) : place === 'recent' ? this.api.recent() : place === 'starred' ? this.api.starred() : this.api.list(this.path());
    req.subscribe({
      next: (r) => {
        this.entries.set(r.entries);
        this.usage.set(r.usage);
        this.loading.set(false);
        this.queueThumbs(r.entries);
      },
      error: (e) => this.fail(e),
    });
  }

  private fail(e: { status?: number; error?: { error?: string } }) {
    this.loading.set(false);
    if (e?.status === 404 && this.place() === 'files' && this.path()) {
      this.toast.show('Esa carpeta ya no existe. Volviste al inicio.', 'warning');
      this.go('files', '');
      return;
    }
    this.error.set(e?.error?.error || 'No se pudo cargar el drive. Revisa tu conexión e inténtalo de nuevo.');
  }

  onSearch(value: string) {
    this.query.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.load(), 250);
  }

  setView(v: 'grid' | 'list') {
    this.view.set(v);
    this.writePref('drive.view', v);
    if (v === 'grid') this.queueThumbs(this.entries());
  }

  setSort(key: SortKey) {
    const cur = this.sort();
    this.sort.set({ key, dir: cur.key === key ? (cur.dir === 1 ? -1 : 1) : key === 'modified' ? -1 : 1 });
  }

  // ── selección ──────────────────────────────────────────────────────────────
  isSelected(e: DriveEntry) {
    return this.selected().has(e.path);
  }

  clearSelection() {
    this.selected.set(new Set());
    this.anchor = -1;
  }

  select(entry: DriveEntry, ev: MouseEvent | KeyboardEvent) {
    const list = this.visible();
    const idx = list.findIndex((e) => e.path === entry.path);
    const next = new Set(this.selected());
    if (ev.shiftKey && this.anchor >= 0) {
      const [a, b] = [Math.min(this.anchor, idx), Math.max(this.anchor, idx)];
      if (!(ev.metaKey || ev.ctrlKey)) next.clear();
      list.slice(a, b + 1).forEach((e) => next.add(e.path));
    } else if (ev.metaKey || ev.ctrlKey) {
      next.has(entry.path) ? next.delete(entry.path) : next.add(entry.path);
      this.anchor = idx;
    } else {
      next.clear();
      next.add(entry.path);
      this.anchor = idx;
    }
    this.selected.set(next);
  }

  selectAll() {
    this.selected.set(new Set(this.visible().map((e) => e.path)));
  }

  // ── menú contextual ────────────────────────────────────────────────────────
  openMenu(ev: MouseEvent, entry: DriveEntry | null) {
    ev.preventDefault();
    ev.stopPropagation();
    if (entry && !this.isSelected(entry)) {
      this.selected.set(new Set([entry.path]));
      this.anchor = this.visible().findIndex((e) => e.path === entry.path);
    }
    if (!entry) this.clearSelection();
    const w = 248;
    const h = entry ? 420 : 200;
    this.menu.set({ x: Math.min(ev.clientX, window.innerWidth - w - 8), y: Math.min(ev.clientY, window.innerHeight - h - 8), target: entry });
  }

  closeMenu() {
    this.menu.set(null);
  }

  canPrint(e: DriveEntry | null) {
    return !!e && e.type === 'file' && PRINTABLE.includes(e.kind);
  }

  isArchive(e: DriveEntry | null) {
    return !!e && e.type === 'file' && /\.(zip|tar|tgz|tar\.gz)$/i.test(e.name);
  }

  // ── operaciones ────────────────────────────────────────────────────────────
  startNewFolder() {
    this.closeMenu();
    if (this.place() !== 'files') this.go('files', this.path());
    this.folderDraft = 'Carpeta nueva';
    this.creatingFolder.set(true);
    setTimeout(() => {
      const el = document.getElementById('drive-new-folder') as HTMLInputElement | null;
      el?.focus();
      el?.select();
    });
  }

  commitNewFolder() {
    const name = this.folderDraft.trim();
    this.creatingFolder.set(false);
    if (!name) return;
    this.api.mkdir(this.path(), name).subscribe({
      next: (entry) => {
        this.reloadWith([entry.path]);
        this.selected.set(new Set([entry.path]));
      },
      error: (e) => this.toast.show(e?.error?.error || 'No se pudo crear la carpeta.', 'error'),
    });
  }

  startRename(entry?: DriveEntry | null) {
    const target = entry ?? this.selectedEntries()[0];
    this.closeMenu();
    if (!target || this.place() === 'trash') return;
    this.renaming.set(target.path);
    this.renameDraft = target.name;
    setTimeout(() => {
      const el = this.renameInput?.nativeElement;
      if (!el) return;
      el.focus();
      const dot = target.type === 'file' ? target.name.lastIndexOf('.') : -1;
      el.setSelectionRange(0, dot > 0 ? dot : target.name.length); // como GNOME: sin la extensión
    });
  }

  commitRename(entry: DriveEntry) {
    const name = this.renameDraft.trim();
    this.renaming.set(null);
    if (!name || name === entry.name) return;
    this.api.rename(entry.path, name).subscribe({
      next: () => this.load(),
      error: (e) => this.toast.show(e?.error?.error || 'No se pudo renombrar.', 'error'),
    });
  }

  cancelRename() {
    this.renaming.set(null);
  }

  copySel(mode: 'copy' | 'cut') {
    const paths = this.selectedEntries().map((e) => e.path);
    this.closeMenu();
    if (!paths.length) return;
    this.clipboard.set({ mode, paths });
    this.toast.show(`${paths.length === 1 ? '1 elemento' : paths.length + ' elementos'} ${mode === 'cut' ? 'para mover' : 'copiados'}. Pégalos en otra carpeta.`, 'info', 2500);
  }

  async paste(dest = this.path()) {
    const clip = this.clipboard();
    this.closeMenu();
    if (!clip || this.place() !== 'files') return;
    const moving = clip.mode === 'cut';
    const label = clip.paths.length === 1 ? clip.paths[0].split('/').pop()! : `${clip.paths.length} elementos`;
    const task = this.startTask(moving ? 'move' : 'copy', label);
    if (moving) await this.animateOut(clip.paths.filter((p) => this.entries().some((e) => e.path === p)));
    const req = moving ? this.api.move(clip.paths, dest) : this.api.copy(clip.paths, dest);
    req.subscribe({
      next: (r) => {
        if (moving) this.clipboard.set(null);
        this.endTask(task);
        this.reloadWith(dest === this.path() ? r.entries.map((e) => e.path) : []);
      },
      error: (e) => {
        this.leaving.set(new Set());
        this.endTask(task, e?.error?.error || 'No se pudo pegar');
        this.toast.show(e?.error?.error || 'No se pudo pegar.', 'error');
      },
    });
  }

  async trashSel() {
    const items = this.selectedEntries();
    this.closeMenu();
    if (!items.length) return;
    await this.animateOut(items.map((e) => e.path));
    this.api.trash(items.map((e) => e.path)).subscribe({
      next: (r) => {
        this.toast.show(r.trashed === 1 ? `«${items[0].name}» se movió a la papelera` : `${r.trashed} elementos a la papelera`, 'success');
        this.clearSelection();
        this.reloadWith();
      },
      error: (e) => {
        this.leaving.set(new Set());
        this.toast.show(e?.error?.error || 'No se pudo eliminar.', 'error');
      },
    });
  }

  toggleStar(entries = this.selectedEntries()) {
    this.closeMenu();
    if (!entries.length) return;
    const on = !entries.every((e) => e.starred);
    this.api.setStarred(entries.map((e) => e.path), on).subscribe({
      next: () => this.load(),
      error: () => this.toast.show('No se pudo cambiar el destacado.', 'error'),
    });
  }

  compressSel() {
    const items = this.selectedEntries();
    this.closeMenu();
    if (!items.length) return;
    const name = items.length === 1 ? items[0].name.replace(/\.[^.]+$/, '') : 'Archivos';
    const dest = this.place() === 'files' ? this.path() : items[0].path.split('/').slice(0, -1).join('/');
    const task = this.startTask('compress', `${name}.zip`);
    this.api.compress(items.map((e) => e.path), dest, name).subscribe({
      next: (z) => {
        this.endTask(task);
        this.reloadWith([z.path]);
        this.selected.set(new Set([z.path]));
      },
      error: (e) => this.endTask(task, e?.error?.error || 'No se pudo comprimir'),
    });
  }

  extractSel(entry = this.selectedEntries()[0]) {
    this.closeMenu();
    if (!this.isArchive(entry)) return;
    const task = this.startTask('extract', entry.name);
    this.api.extract(entry.path).subscribe({
      next: (d) => {
        this.endTask(task);
        this.reloadWith([d.path]);
        this.selected.set(new Set([d.path]));
      },
      error: (e) => this.endTask(task, e?.error?.error || 'No se pudo descomprimir'),
    });
  }

  download(entry = this.selectedEntries()[0]) {
    this.closeMenu();
    if (!entry) return;
    if (entry.type === 'dir') {
      this.toast.show('Para descargar una carpeta, comprímela primero (clic derecho › Comprimir).', 'info');
      return;
    }
    this.api.blob(entry.path).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = entry.name;
        a.click();
        setTimeout(() => URL.revokeObjectURL(url), 4000);
      },
      error: () => this.toast.show('No se pudo descargar.', 'error'),
    });
  }

  // ── papelera ───────────────────────────────────────────────────────────────
  restore(ids: string[]) {
    this.api.restore(ids).subscribe({
      next: (r) => {
        this.toast.show(r.restored === 1 ? 'Restaurado a su carpeta' : `${r.restored} elementos restaurados`, 'success');
        this.load();
      },
      error: (e) => this.toast.show(e?.error?.error || 'No se pudo restaurar.', 'error'),
    });
  }

  async purge(ids?: string[]) {
    const ok = await firstValueFrom(
      this.confirm.confirm({
        title: ids ? 'Eliminar para siempre' : 'Vaciar la papelera',
        message: ids ? 'No podrás recuperar este elemento.' : 'Se eliminará todo lo que hay en la papelera. No podrás recuperarlo.',
        confirmText: ids ? 'Eliminar' : 'Vaciar papelera',
        variant: 'danger',
      }),
    );
    if (!ok) return;
    this.api.emptyTrash(ids).subscribe({
      next: () => this.load(),
      error: (e) => this.toast.show(e?.error?.error || 'No se pudo vaciar.', 'error'),
    });
  }

  // ── subidas ────────────────────────────────────────────────────────────────
  pickFiles() {
    this.closeMenu();
    this.fileInput?.nativeElement.click();
  }

  onFilesPicked(ev: Event) {
    const input = ev.target as HTMLInputElement;
    const files = Array.from(input.files || []).map((f) => ({ file: f, name: f.name }));
    input.value = '';
    this.enqueueUploads(files);
  }

  private async enqueueUploads(items: { file: File; name: string }[], folder = this.path()) {
    if (!items.length) return;
    if (this.place() !== 'files') this.go('files', folder);
    const ops = items.map((it) => ({
      op: { id: ++this.uploadSeq, name: it.name, size: it.file.size, sent: 0, state: 'running', ctrl: new AbortController() } as UploadOp,
      it,
    }));
    this.uploads.update((u) => [...ops.map((o) => o.op), ...u].slice(0, 50));
    // Tres a la vez: rápido sin saturar la conexión ni el servidor.
    const queue = [...ops];
    const arrived: string[] = [];
    const worker = async () => {
      while (queue.length) {
        const { op, it } = queue.shift()!;
        try {
          const entry = await this.api.upload(folder, it.file, it.name, (sent) => this.patchUpload(op.id, { sent }), op.ctrl.signal);
          arrived.push(entry.path.split('/').slice(0, (folder ? folder.split('/').length : 0) + 1).join('/'));
          this.patchUpload(op.id, { state: 'done', sent: op.size });
        } catch (e: unknown) {
          const err = e as { name?: string; error?: { error?: string } };
          this.patchUpload(op.id, err?.name === 'AbortError' ? { state: 'cancelled' } : { state: 'error', error: err?.error?.error || 'Falló la subida' });
        }
      }
    };
    await Promise.all([worker(), worker(), worker()]);
    if (this.place() === 'files' && this.path() === folder) this.reloadWith([...new Set(arrived)]);
  }

  private patchUpload(id: number, patch: Partial<UploadOp>) {
    this.uploads.update((list) => list.map((u) => (u.id === id ? { ...u, ...patch } : u)));
  }

  cancelUpload(op: UploadOp) {
    op.ctrl.abort();
  }

  clearFinished() {
    this.uploads.update((list) => list.filter((u) => u.state === 'running'));
  }

  // ── animaciones de operaciones ─────────────────────────────────────────────
  private reduceMotion() {
    return typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  /** Marca los elementos como «saliendo» y espera la animación antes de seguir. */
  private animateOut(paths: string[]): Promise<void> {
    if (!paths.length || this.reduceMotion()) return Promise.resolve();
    this.leaving.set(new Set(paths));
    return new Promise((resolve) => setTimeout(resolve, LEAVE_MS));
  }

  /** Recarga y resalta lo que llegó (nombres devueltos por el servidor). */
  private reloadWith(paths: string[] = []) {
    this.leaving.set(new Set());
    if (paths.length) {
      this.fresh.set(new Set(paths));
      if (this.freshTimer) clearTimeout(this.freshTimer);
      this.freshTimer = setTimeout(() => this.fresh.set(new Set()), 1600);
    }
    this.load();
  }

  /** Operación larga en el panel de operaciones (barra indeterminada). */
  private startTask(kind: NonNullable<UploadOp['kind']>, name: string): number {
    const id = ++this.uploadSeq;
    this.uploads.update((u) => [{ id, name, size: 0, sent: 0, state: 'running', ctrl: new AbortController(), kind } as UploadOp, ...u].slice(0, 50));
    return id;
  }

  private endTask(id: number, error?: string) {
    this.patchUpload(id, error ? { state: 'error', error } : { state: 'done' });
    if (!error) setTimeout(() => this.uploads.update((l) => l.filter((u) => !(u.id === id && u.state === 'done'))), 2400);
  }

  taskLabel(u: UploadOp) {
    return { compress: 'Comprimiendo', extract: 'Extrayendo', move: 'Moviendo', copy: 'Copiando', upload: 'Subiendo' }[u.kind || 'upload'];
  }

  // ── arrastrar y soltar ─────────────────────────────────────────────────────
  onDragStart(ev: DragEvent, entry: DriveEntry) {
    if (!this.isSelected(entry)) this.selected.set(new Set([entry.path]));
    this.dragPaths = this.selectedEntries().map((e) => e.path);
    ev.dataTransfer?.setData('application/x-drive', JSON.stringify(this.dragPaths));
    if (ev.dataTransfer) {
      ev.dataTransfer.effectAllowed = 'copyMove';
      // Imagen de arrastre propia: el navegador dibujaba el recuadro del elemento, con esquinas rectas.
      const ghost = this.dragGhost(this.selectedEntries());
      ev.dataTransfer.setDragImage(ghost, 18, 18);
      setTimeout(() => ghost.remove(), 0);
    }
  }

  private dragGhost(items: DriveEntry[]): HTMLElement {
    const el = document.createElement('div');
    el.className = 'dv-ghost';
    const isDir = items.length === 1 && items[0].type === 'dir';
    const icon = isDir
      ? '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6.5A1.5 1.5 0 0 1 4.5 5h4.6l2 2H19.5A1.5 1.5 0 0 1 21 8.5v9A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z"/></svg>'
      : '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l5 5v11.5A1.5 1.5 0 0 1 17.5 21h-11A1.5 1.5 0 0 1 5 19.5v-15A1.5 1.5 0 0 1 6.5 3zm7 1.5V9h4.5"/></svg>';
    const label = items.length === 1 ? items[0].name : `${items.length} elementos`;
    el.innerHTML = `<span class="dv-ghost__icon">${icon}</span><span class="dv-ghost__label"></span>`;
    (el.querySelector('.dv-ghost__label') as HTMLElement).textContent = label;
    if (items.length > 1) {
      const badge = document.createElement('span');
      badge.className = 'dv-ghost__count';
      badge.textContent = String(items.length);
      el.appendChild(badge);
    }
    document.body.appendChild(el);
    return el;
  }

  onDragOver(ev: DragEvent, folder: DriveEntry | null = null) {
    if (this.place() !== 'files') return;
    ev.preventDefault();
    const internal = ev.dataTransfer?.types.includes('application/x-drive');
    if (folder && folder.type === 'dir' && !this.dragPaths.includes(folder.path)) this.dropTarget.set(folder.path);
    else if (!internal) this.dropActive.set(true);
  }

  onDragLeave(ev: DragEvent, folder: DriveEntry | null = null) {
    if (folder) this.dropTarget.set(null);
    else if (!(ev.currentTarget as HTMLElement).contains(ev.relatedTarget as Node)) this.dropActive.set(false);
  }

  async onDrop(ev: DragEvent, folder: DriveEntry | null = null) {
    ev.preventDefault();
    ev.stopPropagation();
    this.dropActive.set(false);
    this.dropTarget.set(null);
    if (this.place() !== 'files') return;
    const dest = folder && folder.type === 'dir' ? folder.path : this.path();
    const internal = ev.dataTransfer?.getData('application/x-drive');
    if (internal) {
      const paths: string[] = JSON.parse(internal);
      this.dragPaths = [];
      if (!folder || folder.type !== 'dir' || paths.includes(dest)) return;
      const copy = ev.ctrlKey || ev.altKey;
      const task = this.startTask(copy ? 'copy' : 'move', paths.length === 1 ? paths[0].split('/').pop()! : `${paths.length} elementos`);
      if (!copy) await this.animateOut(paths);
      (copy ? this.api.copy(paths, dest) : this.api.move(paths, dest)).subscribe({
        next: () => {
          this.endTask(task);
          this.reloadWith();
        },
        error: (e) => {
          this.leaving.set(new Set());
          this.endTask(task, e?.error?.error || 'No se pudo mover');
        },
      });
      return;
    }
    const items = await this.collectDropped(ev.dataTransfer);
    this.enqueueUploads(items, dest);
  }

  /** Archivos y carpetas completas arrastrados desde el escritorio (con sus subcarpetas). */
  private async collectDropped(dt: DataTransfer | null): Promise<{ file: File; name: string }[]> {
    if (!dt) return [];
    const out: { file: File; name: string }[] = [];
    const entries = Array.from(dt.items || [])
      .map((i) => (i.kind === 'file' ? (i as DataTransferItem & { webkitGetAsEntry?: () => FileSystemEntry | null }).webkitGetAsEntry?.() : null))
      .filter((e): e is FileSystemEntry => !!e);
    if (!entries.length) return Array.from(dt.files).map((f) => ({ file: f, name: f.name }));
    const walk = async (entry: FileSystemEntry, prefix: string): Promise<void> => {
      if (entry.isFile) {
        const file = await new Promise<File>((res, rej) => (entry as FileSystemFileEntry).file(res, rej));
        out.push({ file, name: prefix + file.name });
      } else if (entry.isDirectory) {
        const reader = (entry as FileSystemDirectoryEntry).createReader();
        let batch: FileSystemEntry[];
        do {
          batch = await new Promise<FileSystemEntry[]>((res, rej) => reader.readEntries(res, rej));
          for (const child of batch) await walk(child, `${prefix}${entry.name}/`);
        } while (batch.length);
      }
    };
    for (const e of entries) await walk(e, '');
    return out;
  }

  // ── miniaturas ─────────────────────────────────────────────────────────────
  private queueThumbs(entries: DriveEntry[]) {
    if (this.view() !== 'grid') return;
    const have = this.thumbs();
    this.thumbQueue = entries.filter((e) => e.kind === 'image' && !have[e.path]).map((e) => e.path);
    for (let i = 0; i < 4; i++) this.nextThumb();
  }

  private nextThumb() {
    if (this.thumbActive >= 4) return;
    const path = this.thumbQueue.shift();
    if (!path) return;
    this.thumbActive++;
    this.api
      .blob(path, 'thumb')
      .pipe(
        finalize(() => {
          this.thumbActive--;
          this.nextThumb();
        }),
      )
      .subscribe({
        next: (blob) => this.thumbs.update((t) => ({ ...t, [path]: URL.createObjectURL(blob) })),
        error: () => undefined,
      });
  }

  icon(e: { kind: DriveKind }): IconProp {
    return ICONS[e.kind] ?? ICONS.file;
  }

  // ── vista rápida ───────────────────────────────────────────────────────────
  openPreview(entry: DriveEntry) {
    this.closeMenu();
    this.closePreview();
    this.previewEntry.set(entry);
    this.previewLoading.set(true);
    this.api.preview(entry.path).subscribe({
      next: (p) => {
        this.preview.set(p);
        if (['image', 'pdf', 'audio', 'video'].includes(p.mode)) {
          const kind = p.mode === 'pdf' && 'converted' in p && p.converted ? 'pdf' : 'file';
          this.api.blob(entry.path, kind).subscribe({
            next: (blob) => {
              const typed = p.mode === 'pdf' ? new Blob([blob], { type: 'application/pdf' }) : blob;
              const url = URL.createObjectURL(typed);
              this.previewUrl.set(url);
              this.previewSafeUrl.set(this.sanitizer.bypassSecurityTrustResourceUrl(url));
              this.previewLoading.set(false);
            },
            error: () => {
              this.preview.set({ mode: 'none', reason: 'No se pudo abrir el archivo.' });
              this.previewLoading.set(false);
            },
          });
        } else this.previewLoading.set(false);
      },
      error: (e) => {
        this.preview.set({ mode: 'none', reason: e?.error?.error || 'No se pudo abrir la vista previa.' });
        this.previewLoading.set(false);
      },
    });
  }

  closePreview() {
    const url = this.previewUrl();
    if (url) URL.revokeObjectURL(url);
    this.previewUrl.set(null);
    this.previewSafeUrl.set(null);
    this.preview.set(null);
    this.previewEntry.set(null);
  }

  stepPreview(delta: number) {
    const files = this.visible().filter((e) => e.type === 'file');
    const cur = this.previewEntry();
    if (!cur || !files.length) return;
    const idx = files.findIndex((e) => e.path === cur.path);
    const next = files[(idx + delta + files.length) % files.length];
    this.selected.set(new Set([next.path]));
    this.openPreview(next);
  }

  safeHtml(html: string) {
    // El HTML lo arma el servidor escapando todo el texto del documento; solo trae etiquetas de formato.
    return this.sanitizer.bypassSecurityTrustHtml(html);
  }

  // ── impresión ──────────────────────────────────────────────────────────────
  private loadPrinters() {
    this.api.printers().subscribe({
      next: (s) => {
        this.printers.set(s);
        if (!this.printForm.printer) this.printForm.printer = s.default || s.printers[0]?.name || '';
      },
      error: () => this.printers.set({ available: false, printers: [], default: null, help: 'No se pudo consultar el servicio de impresión.' }),
    });
  }

  openPrint(entry = this.selectedEntries()[0]) {
    this.closeMenu();
    if (!this.canPrint(entry)) return;
    this.printEntry.set(entry);
    this.printForm = { ...this.printForm, copies: 1, page_range: '', when: 'now', at: this.defaultScheduleTime() };
    this.loadPrinters();
  }

  private defaultScheduleTime() {
    const d = new Date(Date.now() + 60 * 60 * 1000);
    d.setMinutes(0, 0, 0);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  submitPrint() {
    const entry = this.printEntry();
    if (!entry || this.printing()) return;
    const f = this.printForm;
    const scheduled = f.when === 'later' && f.at ? new Date(f.at).toISOString() : null;
    this.printing.set(true);
    this.api
      .print({ path: entry.path, printer: f.printer, copies: f.copies, duplex: f.duplex, color: f.color, page_range: f.page_range || undefined, scheduled_at: scheduled })
      .subscribe({
        next: (job) => {
          this.printing.set(false);
          this.printEntry.set(null);
          this.toast.show(
            job.status === 'scheduled'
              ? `Impresión programada para ${new Date(job.scheduled_at!).toLocaleString('es-PE', { dateStyle: 'medium', timeStyle: 'short' })}`
              : `Enviado a ${job.printer}`,
            'success',
          );
        },
        error: (e) => {
          this.printing.set(false);
          this.toast.show(e?.error?.error || 'No se pudo imprimir.', 'error');
        },
      });
  }

  cancelJob(job: PrintJob) {
    this.api.cancelPrint(job.id).subscribe({
      next: () => this.load(),
      error: (e) => this.toast.show(e?.error?.error || 'No se pudo cancelar.', 'error'),
    });
  }

  // ── atajos de teclado ──────────────────────────────────────────────────────
  @HostListener('document:keydown', ['$event'])
  onKey(ev: KeyboardEvent) {
    const typing = (ev.target as HTMLElement)?.closest('input, textarea, select, [contenteditable]');
    if (this.printEntry()) {
      if (ev.key === 'Escape') this.printEntry.set(null);
      return;
    }
    if (this.previewEntry()) {
      if (ev.key === 'Escape' || ev.key === ' ') {
        ev.preventDefault();
        this.closePreview();
      } else if (ev.key === 'ArrowRight') this.stepPreview(1);
      else if (ev.key === 'ArrowLeft') this.stepPreview(-1);
      return;
    }
    if (ev.key === 'Escape') {
      this.closeMenu();
      if (!typing) this.clearSelection();
      return;
    }
    if (typing) return;
    const mod = ev.metaKey || ev.ctrlKey;
    const sel = this.selectedEntries();
    if (mod && ev.key.toLowerCase() === 'f') {
      ev.preventDefault();
      this.searchInput?.nativeElement.focus();
    } else if (mod && ev.key.toLowerCase() === 'a') {
      ev.preventDefault();
      this.selectAll();
    } else if (mod && ev.key.toLowerCase() === 'c') this.copySel('copy');
    else if (mod && ev.key.toLowerCase() === 'x') this.copySel('cut');
    else if (mod && ev.key.toLowerCase() === 'v') this.paste();
    else if (mod && ev.shiftKey && ev.key.toLowerCase() === 'n') {
      ev.preventDefault();
      this.startNewFolder();
    } else if (ev.key === 'Delete' || (ev.key === 'Backspace' && mod)) this.trashSel();
    else if (ev.key === 'F2') this.startRename();
    else if (ev.key === 'Enter' && sel.length === 1) this.open(sel[0]);
    else if (ev.key === ' ' && sel.length === 1 && sel[0].type === 'file') {
      ev.preventDefault();
      this.openPreview(sel[0]);
    } else if (ev.key === 'Backspace' || (ev.altKey && ev.key === 'ArrowUp')) this.up();
    else if (['ArrowRight', 'ArrowLeft', 'ArrowDown', 'ArrowUp'].includes(ev.key)) this.moveFocus(ev);
  }

  private moveFocus(ev: KeyboardEvent) {
    const list = this.visible();
    if (!list.length) return;
    ev.preventDefault();
    const cur = this.anchor >= 0 ? this.anchor : -1;
    const cols = this.view() === 'grid' ? Math.max(1, Math.floor((document.querySelector('.dv-grid')?.clientWidth || 600) / 132)) : 1;
    const step = { ArrowRight: 1, ArrowLeft: -1, ArrowDown: cols, ArrowUp: -cols }[ev.key as 'ArrowRight'] ?? 0;
    const idx = Math.min(list.length - 1, Math.max(0, cur + step));
    this.select(list[idx], ev);
    document.querySelector<HTMLElement>(`[data-path="${CSS.escape(list[idx].path)}"]`)?.focus();
  }

  @HostListener('document:click')
  onDocClick() {
    this.closeMenu();
  }

  // ── formato ────────────────────────────────────────────────────────────────
  size(bytes: number) {
    if (bytes < 1024) return `${bytes} B`;
    const units = ['KB', 'MB', 'GB', 'TB'];
    let v = bytes / 1024;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(v >= 10 ? 0 : 1).replace('.', ',')} ${units[i]}`;
  }

  when(iso: string | null) {
    if (!iso) return '';
    const d = new Date(iso);
    const today = new Date();
    const sameDay = d.toDateString() === today.toDateString();
    return sameDay ? d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' }) : d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: d.getFullYear() === today.getFullYear() ? undefined : 'numeric' });
  }

  /** Fecha con hora («10 oct., 08:00»): para trabajos de impresión, donde la hora importa. */
  whenFull(iso: string | null) {
    if (!iso) return '';
    return new Date(iso).toLocaleString('es-PE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  detail(e: DriveEntry) {
    return e.type === 'dir' ? (e.items === 1 ? '1 elemento' : `${e.items ?? 0} elementos`) : this.size(e.size);
  }

  folderOf(path: string) {
    const parts = path.split('/');
    parts.pop();
    return parts.join('/') || 'Inicio';
  }

  uploadPct(u: UploadOp) {
    return u.size ? Math.round((u.sent / u.size) * 100) : 100;
  }

  private readPref(key: string, fallback: string) {
    try {
      return localStorage.getItem(key) || fallback;
    } catch {
      return fallback;
    }
  }

  private writePref(key: string, value: string) {
    try {
      localStorage.setItem(key, value);
    } catch {
      /* navegación privada: se ignora */
    }
  }
}
