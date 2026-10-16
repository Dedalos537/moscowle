import { Injectable, signal } from '@angular/core';

export type SplashPhase = 'cover' | 'reveal' | 'done';

/**
 * Pantalla de entrada estilo «reveal mask»: el logo cubre la app (fase `cover`) y al estar lista
 * crece hasta llenar la pantalla, mostrando la app a través de su silueta (`reveal`).
 * Se usa al abrir la app (todos los usuarios) y al terminar de iniciar sesión.
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
}
