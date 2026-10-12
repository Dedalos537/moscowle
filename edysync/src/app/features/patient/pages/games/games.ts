import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import type { IconProp } from '@fortawesome/fontawesome-svg-core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { CatalogGame, GameCatalogService, GameKind } from '../../../../core/services/game-catalog.service';
import { HeaderService } from '../../../../core/services/header.service';
import { PatientService } from '../../../../core/services/patient.service';
import { ToastService } from '../../../../core/services/toast.service';
import { GamePlayer } from '../../../../shared/components/game-player/game-player';

interface TodaySession {
  id: number;
  title: string;
  is_active: boolean;
  games: string[];
}

export const KIND_ICON: Record<GameKind, IconProp> = {
  platformer: ['fas', 'person-running'],
  reflex: ['fas', 'bolt'],
  simulation: ['fas', 'cart-shopping'],
  jclic: ['fas', 'puzzle-piece'],
  clic3: ['fas', 'shapes'],
  flash: ['fas', 'gamepad'],
  html: ['fas', 'gamepad'],
};

/**
 * Juegos del paciente: elegir y jugar. Sin KPIs ni niveles (los ve solo el equipo). Si hay una sesión activa hoy,
 * sus juegos aparecen primero y la partida queda asociada a esa sesión.
 */
@Component({
  selector: 'app-patient-games',
  standalone: true,
  imports: [FontAwesomeModule, GamePlayer],
  templateUrl: './games.html',
  styleUrl: './games.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PatientGames implements OnInit, OnDestroy {
  private catalog = inject(GameCatalogService);
  private patient = inject(PatientService);
  private header = inject(HeaderService);
  private toast = inject(ToastService);

  readonly icon = KIND_ICON;
  readonly games = signal<CatalogGame[]>([]);
  readonly loading = signal(true);
  readonly failed = signal(false);
  readonly session = signal<TodaySession | null>(null);
  readonly playing = signal<CatalogGame | null>(null);

  /** Juegos asignados en la sesión activa de hoy (por nombre de archivo o título). */
  readonly assigned = computed(() => {
    const s = this.session();
    if (!s) return [];
    const wanted = s.games.map((g) => this.norm(g));
    return this.games().filter((g) => wanted.includes(this.norm(g.filename)) || wanted.includes(this.norm(g.title)));
  });
  readonly others = computed(() => {
    const ids = new Set(this.assigned().map((g) => g.id));
    return this.games().filter((g) => !ids.has(g.id));
  });

  ngOnInit() {
    this.header.setConfig({ title: 'Juegos', subtitle: 'Elige un juego y diviértete', icon: ['fas', 'gamepad'] });
    this.load();
  }

  ngOnDestroy() {
    this.header.reset();
  }

  load() {
    this.loading.set(true);
    this.failed.set(false);
    forkJoin({
      catalog: this.catalog.catalog(),
      dashboard: this.patient.getDashboard().pipe(catchError(() => of(null))),
    }).subscribe({
      next: ({ catalog, dashboard }) => {
        this.games.set(catalog.games);
        const today = (dashboard?.data?.today_sessions ?? []) as TodaySession[];
        this.session.set(today.find((s) => s.is_active && s.games?.length) ?? null);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.failed.set(true);
      },
    });
  }

  play(game: CatalogGame) {
    this.playing.set(game);
  }

  onClosed(saved: boolean) {
    this.playing.set(null);
    if (saved) this.toast.show('¡Bien jugado! Tu partida quedó guardada.', 'success');
  }

  sessionFor(game: CatalogGame): number | null {
    return this.assigned().some((g) => g.id === game.id) ? (this.session()?.id ?? null) : null;
  }

  private norm(v: string) {
    return (v || '').toLowerCase().replace(/(\/index)?\.html?$/, '').replace(/[_-]+/g, ' ').trim();
  }
}
