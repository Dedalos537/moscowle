import { type RefObject, useEffect, useRef, useState } from 'react';
import type { SceneController } from './stage';

export type SceneKind = 'hero' | 'path' | 'tower';

export function prefersReducedMotion(): boolean {
  return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Monta una escena three.js en un lienzo. three se descarga aparte, después del primer pintado, para que el texto y
 * los botones de contacto estén listos antes que la ilustración. Si el equipo no tiene WebGL, `failed` lo indica y
 * la sección muestra su versión plana.
 *
 * progress: `section` mide cuánto se recorrió la sección (0 al entrar, 1 al terminar); `leave` mide cuánto salió el
 * bloque de la pantalla por arriba (útil para el hero).
 */
export function useScene(
  kind: SceneKind,
  canvasRef: RefObject<HTMLCanvasElement | null>,
  sectionRef: RefObject<HTMLElement | null>,
  opts: { progress: 'section' | 'leave' | 'enter'; count?: number; pointer?: boolean },
) {
  const [failed, setFailed] = useState(false);
  const [progress, setProgress] = useState(0);
  const controller = useRef<SceneController | null>(null);
  const { count = 4 } = opts;

  useEffect(() => {
    const canvas = canvasRef.current;
    const section = sectionRef.current;
    if (!canvas || !section) return;
    let disposed = false;
    const reduced = prefersReducedMotion();

    const measure = () => {
      const r = section.getBoundingClientRect();
      const vh = window.innerHeight;
      let p: number;
      if (opts.progress === 'leave') p = -r.top / Math.max(1, r.height);
      else if (opts.progress === 'enter') p = r.top < vh * 0.75 ? 1 : 0;
      else p = (vh * 0.55 - r.top) / Math.max(1, r.height - vh * 0.35);
      p = Math.min(1, Math.max(0, p));
      setProgress(Math.round(p * 100) / 100);
      controller.current?.setProgress(p);
    };

    const onPointer = (e: PointerEvent) => {
      controller.current?.setPointer((e.clientX / window.innerWidth) * 2 - 1, (e.clientY / window.innerHeight) * 2 - 1);
    };

    let idle = 0;
    const boot = async () => {
      try {
        const { webglAvailable } = await import('./stage');
        if (!webglAvailable()) throw new Error('sin WebGL');
        let ctrl: SceneController;
        if (kind === 'hero') {
          const m = await import('./heroScene');
          ctrl = m.createHeroScene(canvas, reduced);
        } else if (kind === 'path') {
          const m = await import('./pathScene');
          ctrl = m.createPathScene(canvas, reduced, count);
        } else {
          const m = await import('./towerScene');
          ctrl = m.createTowerScene(canvas, reduced, count);
        }
        if (disposed) {
          ctrl.dispose();
          return;
        }
        controller.current = ctrl;
        canvas.dataset.ready = 'true';
        measure();
      } catch {
        if (!disposed) setFailed(true);
      }
    };

    const ric = (window as Window & { requestIdleCallback?: (cb: () => void, o?: object) => number })
      .requestIdleCallback;
    if (ric) idle = ric(() => void boot(), { timeout: 1200 });
    else idle = window.setTimeout(() => void boot(), 200);

    measure();
    window.addEventListener('scroll', measure, { passive: true });
    window.addEventListener('resize', measure);
    if (opts.pointer) window.addEventListener('pointermove', onPointer, { passive: true });

    return () => {
      disposed = true;
      clearTimeout(idle);
      window.removeEventListener('scroll', measure);
      window.removeEventListener('resize', measure);
      window.removeEventListener('pointermove', onPointer);
      controller.current?.dispose();
      controller.current = null;
    };
    // El tipo de escena y la cantidad de estaciones fijan la escena; el resto se lee en vivo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, count]);

  return { failed, progress };
}
