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
  input,
  output,
  signal,
} from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { CatalogGame, GameCatalogService, GameResult } from '../../../core/services/game-catalog.service';

type Phase = 'loading' | 'playing' | 'saving' | 'closing';

/**
 * Reproductor de juegos a pantalla completa.
 *
 * El juego corre en un iframe del dominio de la API y no guarda nada por su cuenta: envía su resultado con
 * postMessage (vendor/moscowle-bridge.js) y este componente, que ya tiene la sesión del usuario, lo guarda. Al
 * pulsar «Salir» se le pide el resultado de la partida en curso para no perderla.
 * No muestra ningún KPI: el resultado va directo al servidor.
 */
import { HttpClient } from '@angular/common/http';
import { AuthService } from '../../../core/services/auth.service';
@Component({
  selector: 'app-game-player',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './game-player.html',
  styleUrl: './game-player.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GamePlayer implements OnInit, OnDestroy {
  private catalog = inject(GameCatalogService);
  private auth = inject(AuthService);
  private http = inject(HttpClient);
  private sanitizer = inject(DomSanitizer);

  game = input.required<CatalogGame>();
  sessionId = input<number | null>(null);
  /** De quién es el avance guardado en el navegador (niveles, estrellas): el paciente de la sesión.
   * Si no se indica, el usuario con sesión. Así un paciente no ve el avance de otro ni el de una prueba. */
  playerId = input<number | null>(null);
  /** El equipo prueba el juego: la partida no se guarda como si fuera de un paciente. */
  preview = input(false);
  closed = output<boolean>();

  @ViewChild('frame', { static: true }) frame!: ElementRef<HTMLIFrameElement>;
  @ViewChild('shell', { static: true }) shell!: ElementRef<HTMLElement>;

  readonly phase = signal<Phase>('loading');
  readonly saved = signal(false);
  readonly error = signal<string | null>(null);
  readonly fullscreen = signal(false);

  readonly src = computed<SafeResourceUrl>(() =>
    this.sanitizer.bypassSecurityTrustResourceUrl(
      this.catalog.playUrl(this.game(), {
        session_id: this.sessionId(),
        player: this.preview() ? `prueba${this.auth.currentUserId ?? ''}` : (this.playerId() ?? this.auth.currentUserId),
      }),
    ),
  );

  private closeTimer: ReturnType<typeof setTimeout> | null = null;
  private previousFocus: Element | null = null;

  ngOnInit() {
    this.previousFocus = document.activeElement;
    document.body.style.overflow = 'hidden';
  }

  ngOnDestroy() {
    document.body.style.overflow = '';
    if (this.closeTimer) clearTimeout(this.closeTimer);
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined);
    (this.previousFocus as HTMLElement | null)?.focus?.();
  }

  onLoad() {
    this.phase.set('playing');
    // El teclado va al juego desde el primer momento.
    this.frame.nativeElement.focus();
  }

  @HostListener('window:message', ['$event'])
  onMessage(e: MessageEvent) {
    if (e.source !== this.frame.nativeElement.contentWindow || e.origin !== this.catalog.gamesOrigin) return;
    const data = e.data as { source?: string; type?: string; payload?: GameResult };
    if (!data || data.source !== 'moscowle-game') return;
    if (data.type === 'result' && data.payload) this.save(data.payload);
    else if (data.type === 'exit') this.requestClose();
    else if (data.type === 'nothing' && this.phase() === 'closing') this.markPlayed(Number((data.payload as { duration_s?: number })?.duration_s) || 0);
  }

  private save(result: GameResult) {
    if (this.preview()) {
      if (this.phase() === 'closing') this.finish();
      return;
    }
    if (this.saved()) return;
    this.phase.set(this.phase() === 'closing' ? 'closing' : 'saving');
    const payload: GameResult = { ...result, game_id: this.game().id, session_id: this.sessionId() ?? result.session_id ?? null };
    this.catalog.saveResult(payload).subscribe({
      next: () => {
        this.saved.set(true);
        if (this.phase() === 'closing') this.finish();
        else this.phase.set('playing');
      },
      error: () => {
        this.error.set('No pudimos guardar la partida. Revisa tu conexión.');
        if (this.phase() === 'closing') this.finish();
        else this.phase.set('playing');
      },
    });
  }

  /** «Salir»: pide al juego su resultado y espera un momento antes de cerrar. */
  requestClose() {
    if (this.phase() === 'closing') return;
    this.phase.set('closing');
    try {
      this.frame.nativeElement.contentWindow?.postMessage({ source: 'moscowle-player', type: 'collect' }, this.catalog.gamesOrigin);
    } catch {
      /* si el juego no responde, se cierra igual */
    }
    this.closeTimer = setTimeout(() => this.finish(), 1500);
  }

  /** Salió antes de que el juego diera un resultado: en una sesión igual cuenta como realizado (no hace falta
   * terminarlo). Sin sesión, o en una prueba, no se guarda nada. */
  private markPlayed(durationS: number) {
    const sid = this.sessionId();
    if (!sid || this.preview() || this.saved() || durationS < 5) return this.finish();
    this.http.post(`/api/sessions/${sid}/games/${this.game().id}/played`, { duration_s: durationS }).subscribe({
      next: () => {
        this.saved.set(true);
        this.finish();
      },
      error: () => this.finish(),
    });
  }

  private finish() {
    if (this.closeTimer) clearTimeout(this.closeTimer);
    this.closed.emit(this.saved());
  }

  toggleFullscreen() {
    const el = this.shell.nativeElement;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => undefined);
      this.fullscreen.set(false);
    } else if (el.requestFullscreen) {
      el.requestFullscreen().then(() => this.fullscreen.set(true)).catch(() => undefined);
    }
    this.frame.nativeElement.focus();
  }

  @HostListener('document:fullscreenchange')
  onFullscreenChange() {
    this.fullscreen.set(!!document.fullscreenElement);
  }
}
