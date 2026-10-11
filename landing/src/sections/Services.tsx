import { useEffect, useMemo, useRef, useState } from 'react';
import { trackContact } from '../api';
import { type Content, whatsappLink } from '../content';
import { BlockGlyph, WhatsAppIcon } from '../icons';
import type { SorterController } from '../three/sorterScene';
import { prefersReducedMotion } from '../three/useScene';

const SHAPES = ['circle', 'square', 'triangle', 'rect'] as const;
type Shape = (typeof SHAPES)[number];

interface Pick {
  col: number;
  row: number;
}

/**
 * Terapias como un juego de encaje: cada columna del tablero es una categoría (su forma) y cada pieza una terapia.
 * Tocar una pieza la saca del agujero y muestra su información. Los botones de abajo hacen lo mismo con teclado o
 * lector de pantalla, y son la única vía si el equipo no tiene WebGL.
 */
export function Services({ content }: { content: Content }) {
  const categories = useMemo(() => {
    const order: string[] = [];
    for (const s of content.services) if (!order.includes(s.category)) order.push(s.category);
    return order.map((name, i) => ({
      name,
      shape: SHAPES[i % SHAPES.length] as Shape,
      items: content.services.filter((s) => s.category === name),
    }));
  }, [content.services]);

  const [pick, setPick] = useState<Pick>({ col: 0, row: 0 });
  const [failed, setFailed] = useState(false);
  const canvas = useRef<HTMLCanvasElement>(null);
  const section = useRef<HTMLElement>(null);
  const ctrl = useRef<SorterController | null>(null);
  const shape = categories.map((c) => c.items.length).join(',');

  useEffect(() => {
    const el = canvas.current;
    if (!el || !categories.length) return;
    let disposed = false;
    const boot = async () => {
      try {
        const { webglAvailable } = await import('../three/stage');
        if (!webglAvailable()) throw new Error('sin WebGL');
        const { createSorterScene } = await import('../three/sorterScene');
        if (disposed) return;
        const c = createSorterScene(
          el,
          prefersReducedMotion(),
          categories.map((cat) => cat.items.length),
          (col, row) => setPick({ col, row }),
        );
        ctrl.current = c;
        el.dataset.ready = 'true';
        c.select(pick.col, pick.row);
      } catch {
        if (!disposed) setFailed(true);
      }
    };
    const id = window.setTimeout(() => void boot(), 150);
    const onPointer = (e: PointerEvent) => {
      const r = section.current?.getBoundingClientRect();
      if (!r || r.bottom < 0 || r.top > window.innerHeight) return;
      ctrl.current?.setPointer((e.clientX / window.innerWidth) * 2 - 1, 0);
    };
    window.addEventListener('pointermove', onPointer, { passive: true });
    return () => {
      disposed = true;
      clearTimeout(id);
      window.removeEventListener('pointermove', onPointer);
      ctrl.current?.dispose();
      ctrl.current = null;
    };
    // El tablero se rehace solo si cambia cuántas terapias hay por categoría.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shape]);

  const choose = (col: number, row: number) => {
    setPick({ col, row });
    ctrl.current?.select(col, row);
  };

  if (!categories.length) return null;
  const cat = categories[Math.min(pick.col, categories.length - 1)];
  const svc = cat.items[Math.min(pick.row, cat.items.length - 1)];

  return (
    <section ref={section} id="terapias" className="services" aria-labelledby="services-title">
      <div className="section-head">
        <h2 id="services-title">{content.services_intro.title}</h2>
        {content.services_intro.subtitle && <p>{content.services_intro.subtitle}</p>}
      </div>

      <div className="sorter">
        <div className="sorter__board">
          {!failed && (
            <>
              <canvas ref={canvas} className="sorter__canvas" aria-hidden="true" />
              <p className="sorter__hint" aria-hidden="true">
                Toca una pieza para sacarla del tablero
              </p>
            </>
          )}
          <div className="sorter__legend" role="group" aria-label="Categorías">
            {categories.map((c, i) => (
              <button
                key={c.name}
                type="button"
                className="sorter__cat"
                aria-pressed={i === pick.col}
                onClick={() => choose(i, 0)}
              >
                <BlockGlyph shape={c.shape} className={`glyph glyph--${c.shape}`} />
                <span>{c.name}</span>
                <span className="services__count">{c.items.length}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="sorter__info" aria-live="polite">
          <p className="sorter__cat-name">
            <BlockGlyph shape={cat.shape} className={`glyph glyph--${cat.shape}`} />
            {cat.name}
          </p>
          <h3 key={`${cat.name}/${svc.title}`} className="sorter__title">
            {svc.title}
          </h3>
          {svc.image && <img className="sorter__img" src={svc.image} alt="" loading="lazy" width="600" height="400" />}
          <p className="sorter__body">{svc.body}</p>
          <a
            className="btn btn--wa"
            href={whatsappLink(content.contact.whatsapp, `Hola, quiero información sobre ${svc.title} (${cat.name}).`)}
            target="_blank"
            rel="noopener"
            onClick={() => trackContact({ channel: 'whatsapp', service: svc.title })}
          >
            <WhatsAppIcon />
            Preguntar por {svc.title}
          </a>

          <div className="sorter__more">
            <p>En {cat.name.toLowerCase()}</p>
            <ul>
              {cat.items.map((s, row) => (
                <li key={s.title}>
                  <button type="button" aria-pressed={row === pick.row} onClick={() => choose(pick.col, row)}>
                    {s.title}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
