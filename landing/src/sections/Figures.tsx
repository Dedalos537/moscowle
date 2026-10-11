import { useRef } from 'react';
import type { Content } from '../content';
import { BlockGlyph } from '../icons';
import { useScene } from '../three/useScene';

const GLYPHS = ['rect', 'square', 'circle', 'triangle'] as const;

/** Trayectoria: las cifras del centro se apilan como una torre de bloques, de abajo hacia arriba. */
export function Figures({ content }: { content: Content }) {
  const section = useRef<HTMLElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const stats = content.stats.slice(0, 4);
  const { failed } = useScene('tower', canvas, section, { progress: 'enter', count: stats.length });

  if (!stats.length) return null;
  return (
    <section ref={section} className="figures" aria-labelledby="figures-title">
      <div className="figures__stage" aria-hidden="true">
        {!failed && <canvas ref={canvas} className="figures__canvas" />}
      </div>
      <div className="figures__copy">
        <h2 id="figures-title">Una trayectoria que se construye bloque a bloque</h2>
        {/* De arriba hacia abajo, igual que se lee la torre. */}
        <dl className="figures__list">
          {stats
            .map((s, i) => ({ ...s, glyph: GLYPHS[i] }))
            .reverse()
            .map((s) => (
              <div key={s.label}>
                <dt>
                  <BlockGlyph shape={s.glyph} className={`glyph glyph--${s.glyph}`} />
                  {s.label}
                </dt>
                <dd>{s.value}</dd>
              </div>
            ))}
        </dl>
      </div>
    </section>
  );
}
