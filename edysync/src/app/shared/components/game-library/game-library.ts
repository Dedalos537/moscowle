import { ChangeDetectionStrategy, Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { KeyValuePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import {
  CatalogGame,
  GameCatalogService,
  GameKind,
  GameLevelsResponse,
  KpiKey,
  KpiProfile,
  KpiSpec,
  LevelId,
  LevelSpec,
} from '../../../core/services/game-catalog.service';
import { ToastService } from '../../../core/services/toast.service';
import { GamePlayer } from '../game-player/game-player';

type Tab = 'levels' | 'info' | 'kpis';
type KindFilter = 'all' | GameKind;

const KIND_ICON: Record<GameKind, IconProp> = {
  platformer: ['fas', 'person-running'],
  reflex: ['fas', 'bolt'],
  simulation: ['fas', 'cart-shopping'],
  jclic: ['fas', 'puzzle-piece'],
  clic3: ['fas', 'shapes'],
  flash: ['fas', 'gamepad'],
  html: ['fas', 'gamepad'],
};

interface KpiRow {
  key: KpiKey;
  spec: KpiSpec;
  on: boolean;
  t: [number | null, number | null, number | null];
}

/**
 * Biblioteca de juegos para el equipo: catálogo, prueba, niveles de KPI por paciente y (admin) ficha, umbrales,
 * subida y archivo. Los pacientes no usan este componente: su vista es /patient/games, sin KPIs.
 */
@Component({
  selector: 'app-game-library',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule, GamePlayer, KeyValuePipe],
  templateUrl: './game-library.html',
  styleUrl: './game-library.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GameLibrary implements OnInit {
  private api = inject(GameCatalogService);
  private toast = inject(ToastService);

  /** admin: edita y sube; therapist: consulta niveles de sus pacientes. */
  mode = input<'admin' | 'therapist' | 'supervisor'>('therapist');

  readonly icon = KIND_ICON;
  readonly games = signal<CatalogGame[]>([]);
  readonly kpiCatalog = signal<KpiSpec[]>([]);
  readonly levelSpecs = signal<LevelSpec[]>([]);
  readonly kinds = signal<Record<string, string>>({});
  readonly loading = signal(true);
  readonly failed = signal(false);

  readonly search = signal('');
  readonly kindFilter = signal<KindFilter>('all');
  readonly showArchived = signal(false);

  readonly selectedId = signal<number | null>(null);
  readonly tab = signal<Tab>('levels');
  readonly levels = signal<GameLevelsResponse | null>(null);
  readonly levelsLoading = signal(false);
  readonly expanded = signal<number | null>(null);

  readonly preview = signal<CatalogGame | null>(null);

  // Ficha (admin)
  form = { title: '', description: '', area: '', ages: '', kind: 'html' as GameKind, is_active: true };
  readonly saving = signal(false);
  readonly formError = signal<string | null>(null);
  kpiRows: KpiRow[] = [];

  // Subida
  readonly uploadOpen = signal(false);
  readonly uploading = signal(false);
  readonly uploadError = signal<string | null>(null);
  readonly uploadReport = signal<{ title: string; activities?: number; warnings?: string[] } | null>(null);
  uploadFile: File | null = null;
  uploadTitle = '';

  readonly canEdit = computed(() => this.mode() === 'admin');

  readonly filtered = computed(() => {
    const q = this.search().trim().toLowerCase();
    const kind = this.kindFilter();
    return this.games().filter(
      (g) =>
        (this.showArchived() || g.is_active) &&
        (kind === 'all' || g.kind === kind || (kind === 'jclic' && g.kind === 'clic3')) &&
        (!q || g.title.toLowerCase().includes(q) || (g.area ?? '').toLowerCase().includes(q)),
    );
  });

  readonly kindChips = computed(() => {
    const present = new Set<GameKind>(this.games().map((g) => (g.kind === 'clic3' ? 'jclic' : g.kind)));
    const labels: Record<string, string> = { platformer: 'Plataformas', simulation: 'Simulación', reflex: 'Reflejos', jclic: 'Actividades', flash: 'Flash', html: 'Web' };
    return (['platformer', 'simulation', 'jclic', 'reflex', 'flash', 'html'] as GameKind[]).filter((k) => present.has(k)).map((k) => ({ id: k, label: labels[k] }));
  });

  readonly archivedCount = computed(() => this.games().filter((g) => !g.is_active).length);
  readonly selected = computed(() => this.games().find((g) => g.id === this.selectedId()) ?? null);

  readonly distribution = computed(() => {
    const lv = this.levels();
    if (!lv) return [];
    const total = Object.values(lv.distribution).reduce((a, b) => a + b, 0);
    return lv.levels.map((l) => ({ ...l, n: lv.distribution[l.id] ?? 0, pct: total ? ((lv.distribution[l.id] ?? 0) / total) * 100 : 0 }));
  });

  ngOnInit() {
    this.load();
  }

  load() {
    this.loading.set(true);
    this.failed.set(false);
    this.api.catalog().subscribe({
      next: (r) => {
        this.games.set(r.games);
        this.kpiCatalog.set(r.kpi_catalog ?? []);
        this.levelSpecs.set(r.levels ?? []);
        this.kinds.set(r.kinds ?? {});
        this.loading.set(false);
        const sel = this.selected();
        if (sel) this.fillForm(sel);
      },
      error: () => {
        this.loading.set(false);
        this.failed.set(true);
      },
    });
  }

  // ───────────────────────── detalle ─────────────────────────

  open(game: CatalogGame, tab: Tab = 'levels') {
    this.selectedId.set(game.id);
    this.tab.set(tab);
    this.fillForm(game);
    this.expanded.set(null);
    this.loadLevels(game.id);
  }

  close() {
    this.selectedId.set(null);
    this.levels.set(null);
  }

  private loadLevels(id: number) {
    this.levelsLoading.set(true);
    this.levels.set(null);
    this.api.levels(id).subscribe({
      next: (r) => {
        if (this.selectedId() === id) this.levels.set(r);
        this.levelsLoading.set(false);
      },
      error: () => this.levelsLoading.set(false),
    });
  }

  levelLabel(id: LevelId | null): string {
    return this.levelSpecs().find((l) => l.id === id)?.label ?? 'Sin datos';
  }

  formatValue(value: number, unit: string): string {
    const v = Number.isInteger(value) ? value : value.toFixed(1);
    if (unit === '%') return `${v}%`;
    if (unit === 's') return `${v} s`;
    return String(v);
  }

  when(iso: string | null): string {
    if (!iso) return '—';
    const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : `${iso}Z`);
    const days = Math.floor((Date.now() - d.getTime()) / 86400000);
    if (days <= 0) return 'hoy';
    if (days === 1) return 'ayer';
    if (days < 7) return `hace ${days} días`;
    return d.toLocaleDateString('es-PE', { day: 'numeric', month: 'short' });
  }

  // ───────────────────────── ficha e indicadores (admin) ─────────────────────────

  private fillForm(g: CatalogGame) {
    this.form = {
      title: g.title,
      description: g.description ?? '',
      area: g.area ?? '',
      ages: g.ages ?? '',
      kind: g.kind,
      is_active: g.is_active,
    };
    this.formError.set(null);
    const profile = g.kpis ?? {};
    this.kpiRows = this.kpiCatalog().map((spec) => {
      const t = profile[spec.key];
      return { key: spec.key, spec, on: !!t, t: t ? [t[0], t[1], t[2]] : [null, null, null] };
    });
  }

  saveInfo() {
    const g = this.selected();
    if (!g || this.saving()) return;
    if (!this.form.title.trim()) return this.formError.set('El nombre es obligatorio.');
    this.saving.set(true);
    this.api
      .update(g.id, {
        title: this.form.title.trim(),
        description: this.form.description.trim(),
        area: this.form.area.trim(),
        ages: this.form.ages.trim(),
        kind: this.form.kind,
        is_active: this.form.is_active,
      })
      .subscribe({
        next: (r) => this.applySaved(r.game, 'Ficha guardada'),
        error: (e: HttpErrorResponse) => this.failSave(e),
      });
  }

  saveKpis() {
    const g = this.selected();
    if (!g || this.saving()) return;
    const profile: KpiProfile = {};
    for (const row of this.kpiRows) {
      if (!row.on) continue;
      if (row.t.some((v) => v === null || Number.isNaN(Number(v)))) {
        return this.formError.set(`${row.spec.label}: completa los tres umbrales.`);
      }
      profile[row.key] = row.t.map(Number) as [number, number, number];
    }
    if (!Object.keys(profile).length) return this.formError.set('Activa al menos un indicador.');
    this.saving.set(true);
    this.api.update(g.id, { kpis: profile }).subscribe({
      next: (r) => {
        this.applySaved(r.game, 'Umbrales guardados');
        this.loadLevels(g.id);
      },
      error: (e: HttpErrorResponse) => this.failSave(e),
    });
  }

  resetKpis() {
    const g = this.selected();
    if (!g || !confirm('¿Volver a los umbrales recomendados para este tipo de juego?')) return;
    this.saving.set(true);
    this.api.update(g.id, { kpis: null }).subscribe({
      next: (r) => {
        this.applySaved(r.game, 'Umbrales restaurados');
        this.loadLevels(g.id);
      },
      error: (e: HttpErrorResponse) => this.failSave(e),
    });
  }

  private applySaved(game: CatalogGame, msg: string) {
    this.saving.set(false);
    this.formError.set(null);
    this.games.update((list) => list.map((x) => (x.id === game.id ? game : x)));
    this.fillForm(game);
    this.toast.show(msg, 'success');
  }

  private failSave(e: HttpErrorResponse) {
    this.saving.set(false);
    this.formError.set(e.error?.error || 'No se pudo guardar. Inténtalo de nuevo.');
  }

  thresholdHint(row: KpiRow): string {
    return row.spec.better === 'high' ? 'De menor a mayor: subir el número exige más.' : 'De mayor a menor: menos es mejor.';
  }

  archive() {
    const g = this.selected();
    if (!g) return;
    if (!confirm(`¿Quitar «${g.title}» del catálogo? Si tiene partidas registradas, se archiva y su historial se conserva.`)) return;
    this.api.remove(g.id).subscribe({
      next: (r) => {
        if (r.archived) {
          this.games.update((list) => list.map((x) => (x.id === g.id ? { ...x, is_active: false } : x)));
          this.toast.show(`Archivado: tiene ${r.plays} partidas registradas`, 'success');
        } else {
          this.games.update((list) => list.filter((x) => x.id !== g.id));
          this.toast.show('Juego eliminado', 'success');
        }
        this.close();
      },
      error: (e: HttpErrorResponse) => this.toast.show(e.error?.error || 'No se pudo quitar el juego', 'error'),
    });
  }

  // ───────────────────────── subida ─────────────────────────

  openUpload() {
    this.uploadOpen.set(true);
    this.uploadFile = null;
    this.uploadTitle = '';
    this.uploadError.set(null);
    this.uploadReport.set(null);
  }

  onFile(event: Event) {
    const file = (event.target as HTMLInputElement).files?.[0] ?? null;
    this.uploadFile = file;
    if (file && !this.uploadTitle) {
      this.uploadTitle = file.name
        .replace(/\.(jclic\.zip|zip|html?|swf|pac|pcc)$/i, '')
        .replace(/[_-]+/g, ' ')
        .trim();
    }
  }

  upload() {
    if (!this.uploadFile || !this.uploadTitle.trim() || this.uploading()) return;
    this.uploading.set(true);
    this.uploadError.set(null);
    this.api.upload(this.uploadFile, this.uploadTitle.trim()).subscribe({
      next: (r) => {
        this.uploading.set(false);
        this.uploadReport.set({ title: r.game?.title ?? this.uploadTitle, activities: r.activities, warnings: r.warnings });
        this.load();
      },
      error: (e: HttpErrorResponse) => {
        this.uploading.set(false);
        this.uploadError.set(e.error?.error || 'No se pudo subir el archivo.');
      },
    });
  }
}
