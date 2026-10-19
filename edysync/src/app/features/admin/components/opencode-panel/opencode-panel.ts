import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { AdminService, OpencodeInstance, OpencodeStatus } from '../../../../core/services/admin.service';

/** PRP 009: interruptores de opencode (MiMo-V2.6-Flash Free) en Visor → LLM. */
@Component({
  selector: 'app-opencode-panel',
  imports: [FontAwesomeModule],
  templateUrl: './opencode-panel.html',
  styleUrl: './opencode-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OpencodePanel {
  private admin = inject(AdminService);
  private destroyRef = inject(DestroyRef);

  readonly status = signal<OpencodeStatus | null>(null);
  readonly loading = signal(true);
  readonly saving = signal<'enabled' | 'dev_mode' | null>(null);
  readonly error = signal<string | null>(null);

  constructor() {
    this.load();
  }

  load() {
    this.loading.set(true);
    this.admin
      .opencodeStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (s) => {
          this.status.set(s);
          this.loading.set(false);
          this.error.set(null);
        },
        error: (err) => {
          this.loading.set(false);
          this.error.set(err?.error?.error || 'No se pudo leer el estado de opencode.');
        },
      });
  }

  toggle(field: 'enabled' | 'dev_mode') {
    const current = this.status();
    if (!current || this.saving()) return;
    this.saving.set(field);
    this.admin
      .saveOpencode({ [field]: !current[field] })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (s) => {
          this.status.set(s);
          this.saving.set(null);
          this.error.set(null);
        },
        error: (err) => {
          this.saving.set(null);
          this.error.set(err?.error?.error || 'No se pudo guardar el cambio.');
        },
      });
  }

  state(inst: OpencodeInstance | undefined): { label: string; tone: 'ok' | 'warn' | 'off' } {
    if (!inst?.configured) return { label: 'Sin instalar', tone: 'off' };
    if (inst.blocked) return { label: `En pausa ${Math.ceil(inst.blocked_for / 60)} min`, tone: 'warn' };
    return inst.online ? { label: 'En línea', tone: 'ok' } : { label: 'Sin respuesta', tone: 'warn' };
  }

  usage(route: string): string {
    const u = this.status()?.usage_today?.[route];
    if (!u) return 'Sin uso hoy';
    const k = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`);
    return `${u.calls} llamadas · ${k(u.tokens_in)} tokens${u.errors ? ` · ${u.errors} con error` : ''}`;
  }
}
