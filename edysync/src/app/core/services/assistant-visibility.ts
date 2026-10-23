import { HttpClient } from '@angular/common/http';
import { Injectable, inject, signal } from '@angular/core';

export interface AssistantVisibility {
  admin: boolean;
  terapista: boolean;
  jugador: boolean;
}

/**
 * Si el botón flotante del asistente aparece para el usuario actual (ajuste del centro por tipo de usuario).
 * Lo cambia un admin en Configuración → IA y modelos; mientras carga se asume oculto (no parpadea).
 */
@Injectable({ providedIn: 'root' })
export class AssistantVisibilityService {
  private http = inject(HttpClient);
  readonly visible = signal(false);
  readonly settings = signal<AssistantVisibility>({ admin: true, terapista: false, jugador: false });

  load(): void {
    this.http.get<AssistantVisibility & { visible: boolean }>('/api/assistant/visibility').subscribe({
      next: (res) => this.apply(res),
      error: () => this.visible.set(false),
    });
  }

  set(role: keyof AssistantVisibility, on: boolean): void {
    const next = { ...this.settings(), [role]: on };
    this.settings.set(next);
    this.http.put<AssistantVisibility & { visible: boolean }>('/api/assistant/visibility', { [role]: on }).subscribe({
      next: (res) => this.apply(res),
      error: () => this.load(),
    });
  }

  private apply(res: AssistantVisibility & { visible: boolean }): void {
    this.settings.set({ admin: res.admin, terapista: res.terapista, jugador: res.jugador });
    this.visible.set(!!res.visible);
  }
}
