import { ChangeDetectionStrategy, Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
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

  status = signal<ChatLinkStatus | null>(null);
  loading = signal(true);
  generating = signal(false);
  unlinking = signal(false);
  code = signal('');
  error = signal('');
  justLinked = signal(false);
  copied = signal(false);
  confirmingChatId = signal<number | null>(null);

  private expiresAt = signal(0);
  private now = signal(Date.now());
  private tickTimer: ReturnType<typeof setInterval> | null = null;
  private pollTimer: ReturnType<typeof setInterval> | null = null;
  private copiedTimer: ReturnType<typeof setTimeout> | null = null;

  accounts = computed<ChatAccount[]>(() => this.status()?.accounts ?? []);
  linked = computed(() => this.status()?.linked ?? false);
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

  constructor() {
    this.destroyRef.onDestroy(() => this.stopTimers());
  }

  ngOnInit(): void {
    this.refresh(false);
  }

  generate(): void {
    if (this.generating()) return;
    this.generating.set(true);
    this.error.set('');
    this.justLinked.set(false);
    this.service.requestCode().subscribe({
      next: (res) => {
        this.code.set(res.code);
        this.expiresAt.set(Date.now() + res.expires_in * 1000);
        this.now.set(Date.now());
        this.generating.set(false);
        this.startTimers();
      },
      error: () => {
        this.error.set('No se pudo generar el código. Inténtalo de nuevo.');
        this.generating.set(false);
      },
    });
  }

  async copy(): Promise<void> {
    try {
      await navigator.clipboard.writeText(`/login ${this.code()}`);
      this.copied.set(true);
      if (this.copiedTimer) clearTimeout(this.copiedTimer);
      this.copiedTimer = setTimeout(() => this.copied.set(false), COPIED_MS);
    } catch {
      this.error.set('No se pudo copiar. Selecciona el comando y cópialo a mano.');
    }
  }

  askUnlink(chatId: number): void {
    this.confirmingChatId.set(chatId);
  }

  cancelUnlink(): void {
    this.confirmingChatId.set(null);
  }

  confirmUnlink(chatId: number): void {
    if (this.unlinking()) return;
    this.unlinking.set(true);
    this.error.set('');
    this.service.unlink(chatId).subscribe({
      next: () => {
        this.unlinking.set(false);
        this.confirmingChatId.set(null);
        this.refresh(false);
      },
      error: () => {
        this.unlinking.set(false);
        this.error.set('No se pudo cerrar la sesión del chat. Inténtalo de nuevo.');
      },
    });
  }

  accountName(account: ChatAccount): string {
    if (account.username) return `@${account.username}`;
    return account.first_name || `Chat ${account.chat_id}`;
  }

  private refresh(polling: boolean): void {
    this.service.getStatus().subscribe({
      next: (status) => {
        const wasLinked = this.linked();
        this.status.set(status);
        this.loading.set(false);
        if (polling && status.linked && !wasLinked) {
          this.justLinked.set(true);
          this.code.set('');
          this.stopTimers();
        }
      },
      error: () => {
        this.loading.set(false);
        if (!polling) this.error.set('No se pudo consultar el estado del chat.');
      },
    });
  }

  private startTimers(): void {
    this.stopTimers();
    this.tickTimer = setInterval(() => {
      this.now.set(Date.now());
      if (this.remaining() === 0) this.stopTimers();
    }, TICK_MS);
    this.pollTimer = setInterval(() => this.refresh(true), POLL_MS);
  }

  private stopTimers(): void {
    if (this.tickTimer) clearInterval(this.tickTimer);
    if (this.pollTimer) clearInterval(this.pollTimer);
    if (this.copiedTimer) clearTimeout(this.copiedTimer);
    this.tickTimer = this.pollTimer = this.copiedTimer = null;
  }
}
