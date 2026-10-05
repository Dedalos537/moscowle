import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  OnInit,
  afterNextRender,
  computed,
  inject,
  output,
  signal,
} from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { ChatAccount, ChatLinkService, ChatLinkStatus } from '../../../core/services/chat-link.service';
import { Alert } from '../alert/alert';
import { Button } from '../button/button';
import { Spinner } from '../spinner/spinner';

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  supervisor: 'Supervisor',
  terapista: 'Terapeuta',
  jugador: 'Paciente',
};

const TICK_MS = 1000;
const POLL_MS = 4000;
const COPIED_MS = 2000;

/** Inicio de sesión en el bot de Telegram: estado del vínculo, código de un solo uso y cierre de sesión del chat. */
@Component({
  selector: 'app-chat-link',
  standalone: true,
  imports: [FontAwesomeModule, Alert, Button, Spinner],
  templateUrl: './chat-link.html',
  styleUrl: './chat-link.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ChatLink implements OnInit {
  private service = inject(ChatLinkService);
  private destroyRef = inject(DestroyRef);
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  private injector = inject(Injector);

  /** Se emite cuando cambia el conjunto de chats vinculados (vincular o desvincular), para que el host se resincronice. */
  linkedChange = output<void>();

  status = signal<ChatLinkStatus | null>(null);
  loading = signal(true);
  generating = signal(false);
  unlinking = signal(false);
  error = signal('');
  justLinked = signal(false);
  copied = signal(false);
  confirmingChatId = signal<number | null>(null);
  /** Texto para lectores de pantalla: solo hitos (código generado, vencido, copiado), nunca la cuenta regresiva. */
  announcement = signal('');

  private now = signal(Date.now());
  private tickTimer: ReturnType<typeof setInterval> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private copiedTimer: ReturnType<typeof setTimeout> | null = null;
  private pollInFlight = false;
  private pollFailures = 0;

  code = computed(() => this.service.pendingCode()?.code ?? '');
  private expiresAt = computed(() => this.service.pendingCode()?.expiresAt ?? 0);
  accounts = computed<ChatAccount[]>(() => this.status()?.accounts ?? []);
  linked = computed(() => this.status()?.linked ?? false);
  botUsername = computed(() => this.status()?.bot_username ?? null);
  roleLabel = computed(() => {
    const role = this.status()?.role ?? '';
    return ROLE_LABELS[role] ?? role;
  });
  remaining = computed(() => Math.max(0, Math.ceil((this.expiresAt() - this.now()) / 1000)));
  hasCode = computed(() => this.code() !== '');
  expired = computed(() => this.hasCode() && this.remaining() === 0);
  countdown = computed(() => {
    const s = this.remaining();
    return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
  });
  /** Enlace directo: Telegram abre el bot y, al pulsar START, envía `/start login_CODIGO` (inicia sesión sin teclear). */
  openUrl = computed(() => {
    const bot = this.botUsername();
    return bot && this.hasCode() && !this.expired() ? `https://t.me/${bot}?start=login_${this.code()}` : '';
  });

  constructor() {
    this.destroyRef.onDestroy(() => {
      this.stopTimers();
      if (this.copiedTimer) clearTimeout(this.copiedTimer);
    });
  }

  ngOnInit(): void {
    this.refresh(false);
    // El menú se destruye al cerrarse: si el código sigue vigente se retoma la cuenta regresiva.
    const pending = this.service.pendingCode();
    if (pending) {
      if (pending.expiresAt > Date.now()) {
        this.now.set(Date.now());
        this.startTimers();
      } else {
        this.service.pendingCode.set(null);
      }
    }
  }

  generate(): void {
    if (this.generating()) return;
    this.generating.set(true);
    this.error.set('');
    this.justLinked.set(false);
    this.service.requestCode().subscribe({
      next: (res) => {
        this.service.pendingCode.set({ code: res.code, expiresAt: Date.now() + res.expires_in * 1000 });
        this.now.set(Date.now());
        this.generating.set(false);
        this.announcement.set(`Código generado. Vence en ${Math.round(res.expires_in / 60)} minutos.`);
        this.startTimers();
      },
      error: () => {
        this.error.set('No se pudo generar el código. Inténtalo de nuevo.');
        this.generating.set(false);
      },
    });
  }

  async copy(): Promise<void> {
    const command = `/login ${this.code()}`;
    let ok = false;
    try {
      await navigator.clipboard.writeText(command);
      ok = true;
    } catch {
      // Sin contexto seguro (la LAN sirve la app por HTTP) no existe la API moderna.
      ok = this.fallbackCopy(command);
    }
    if (ok) {
      this.copied.set(true);
      this.announcement.set('Comando copiado.');
      if (this.copiedTimer) clearTimeout(this.copiedTimer);
      this.copiedTimer = setTimeout(() => this.copied.set(false), COPIED_MS);
    } else {
      this.error.set('No se pudo copiar. Mantén pulsado el comando para seleccionarlo y cópialo.');
    }
  }

  askUnlink(chatId: number): void {
    this.confirmingChatId.set(chatId);
    this.focus('[data-focus="cancel-unlink"] button'); // la opción segura
  }

  cancelUnlink(): void {
    const chatId = this.confirmingChatId();
    this.confirmingChatId.set(null);
    this.focus(`[data-focus="unlink-${chatId}"] button`);
  }

  confirmUnlink(chatId: number): void {
    if (this.unlinking()) return;
    this.unlinking.set(true);
    this.error.set('');
    this.service.unlink(chatId).subscribe({
      next: () => {
        this.unlinking.set(false);
        this.confirmingChatId.set(null);
        this.announcement.set('Chat desvinculado.');
        this.refresh(false, () => this.linkedChange.emit());
        this.focus('[data-focus="generate"] button');
      },
      error: () => {
        this.unlinking.set(false);
        this.error.set('No se pudo desvincular el chat. Inténtalo de nuevo.');
      },
    });
  }

  accountName(account: ChatAccount): string {
    if (account.username) return `@${account.username}`;
    return account.first_name || `Chat ${account.chat_id}`;
  }

  private focus(selector: string): void {
    // Tras el cambio de estado el botón enfocado deja de existir: sin esto el foco cae al <body>.
    afterNextRender(() => this.host.nativeElement.querySelector<HTMLElement>(selector)?.focus(), {
      injector: this.injector,
    });
  }

  private fallbackCopy(text: string): boolean {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.setAttribute('aria-hidden', 'true');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try {
      ok = document.execCommand('copy');
    } catch {
      ok = false;
    }
    document.body.removeChild(area);
    return ok;
  }

  private refresh(polling: boolean, afterLoad?: () => void): void {
    if (polling) {
      if (this.pollInFlight) return; // sin acumular peticiones si el servidor tarda más que el intervalo
      this.pollInFlight = true;
    }
    this.service.getStatus().subscribe({
      next: (status) => {
        const before = new Set(this.accounts().map((a) => a.chat_id));
        this.status.set(status);
        this.loading.set(false);
        this.pollFailures = 0;
        this.pollInFlight = false;
        // Vínculo nuevo = aparece un chat que antes no estaba (sirve también para "Vincular otro chat").
        const gained = status.accounts.some((a) => !before.has(a.chat_id));
        if (polling && gained) {
          this.justLinked.set(true);
          this.announcement.set('Chat vinculado.');
          this.service.pendingCode.set(null);
          this.stopTimers();
          this.linkedChange.emit();
        }
        afterLoad?.();
      },
      error: () => {
        this.loading.set(false);
        this.pollInFlight = false;
        if (!polling) {
          this.error.set('No se pudo consultar el estado del chat.');
        } else if (++this.pollFailures >= 3) {
          this.error.set('Sin conexión: no podemos confirmar el vínculo. Se reintentará en cuanto vuelva.');
        }
      },
    });
  }

  private startTimers(): void {
    this.stopTimers();
    this.tickTimer = setInterval(() => {
      this.now.set(Date.now());
      if (this.remaining() === 0) {
        this.announcement.set('El código venció. Genera uno nuevo.');
        this.stopTimers();
      }
    }, TICK_MS);
    this.pollTimer = setInterval(() => {
      if (document.visibilityState === 'visible') this.refresh(true);
    }, POLL_MS);
  }

  private stopTimers(): void {
    if (this.tickTimer) clearInterval(this.tickTimer);
    if (this.pollTimer) clearInterval(this.pollTimer);
    this.tickTimer = this.pollTimer = null;
  }
}
