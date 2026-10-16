import { Injectable, signal } from '@angular/core';

export type SplashPhase = 'closing' | 'cover' | 'reveal' | 'done';

/**
 * Pantalla de entrada estilo «reveal mask»: el logo cubre la app (fase `cover`) y al estar lista
 * crece hasta llenar la pantalla, mostrando la app a través de su silueta (`reveal`).
 * Se usa al abrir la app (todos los usuarios) y al terminar de iniciar sesión. Al cerrar sesión corre al revés
 * (`closeThen`): la silueta se cierra sobre el panel, se cierra la sesión y el logo vuelve a abrirse sobre el login.
 */
@Injectable({ providedIn: 'root' })
export class SplashService {
  readonly phase = signal<SplashPhase>('cover');

  /** Cubre la pantalla al instante (p. ej. justo después de iniciar sesión, antes de navegar). */
  cover(): void {
    this.phase.set('cover');
  }

  /** Muestra la app a través del logo. Idempotente. */
  reveal(): void {
    if (this.phase() === 'cover') this.phase.set('reveal');
  }

  /** Lo llama el splash al terminar la animación. */
  finish(): void {
    this.phase.set('done');
  }

  private pending: (() => void) | null = null;
  private safety?: ReturnType<typeof setTimeout>;

  /** Cierra la silueta sobre la pantalla actual y luego ejecuta `then` (p. ej. cerrar sesión y navegar). */
  closeThen(then: () => void): void {
    this.pending = then;
    this.phase.set('closing');
    // Por si la animación no termina (pestaña en segundo plano, movimiento reducido): igual se cierra sesión.
    clearTimeout(this.safety);
    this.safety = setTimeout(() => this.closed(), 1400);
  }

  /** Lo llama el splash al terminar de cerrarse. */
  closed(): void {
    clearTimeout(this.safety);
    if (this.phase() !== 'closing') return;
    this.phase.set('cover');
    const then = this.pending;
    this.pending = null;
    then?.();
  }
}
