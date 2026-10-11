import { useMemo, useState } from 'react';
import { trackContact } from '../api';
import { type Content, whatsappLink } from '../content';
import { BlockGlyph, ChevronIcon, WhatsAppIcon } from '../icons';

const SHAPES = ['circle', 'square', 'triangle', 'rect'] as const;
type Shape = (typeof SHAPES)[number];

/** Terapias agrupadas por categoría. Cada fila se despliega con su descripción y un atajo a WhatsApp. */
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

  const [current, setCurrent] = useState(0);
  const [open, setOpen] = useState<string | null>(null);
  const cat = categories[Math.min(current, categories.length - 1)];
  if (!cat) return null;

  const onKey = (e: React.KeyboardEvent, i: number) => {
    const delta = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
    if (!delta) return;
    e.preventDefault();
    const next = (i + delta + categories.length) % categories.length;
    setCurrent(next);
    document.getElementById(`tab-${next}`)?.focus();
  };

  return (
    <section id="terapias" className="services" aria-labelledby="services-title">
      <div className="section-head">
        <h2 id="services-title">{content.services_intro.title}</h2>
        {content.services_intro.subtitle && <p>{content.services_intro.subtitle}</p>}
      </div>

      <div className="services__tabs" role="tablist" aria-label="Categorías">
        {categories.map((c, i) => (
          <button
            key={c.name}
            id={`tab-${i}`}
            role="tab"
            type="button"
            aria-selected={i === current}
            aria-controls="services-panel"
            tabIndex={i === current ? 0 : -1}
            className="services__tab"
            onClick={() => setCurrent(i)}
            onKeyDown={(e) => onKey(e, i)}
          >
            <BlockGlyph shape={c.shape} className={`glyph glyph--${c.shape}`} />
            <span>{c.name}</span>
            <span className="services__count">{c.items.length}</span>
          </button>
        ))}
      </div>

      <ul id="services-panel" role="tabpanel" aria-labelledby={`tab-${current}`} className="services__list">
        {cat.items.map((s) => {
          const key = `${cat.name}/${s.title}`;
          const isOpen = open === key;
          const panel = `svc-${key.replace(/\W+/g, '-')}`;
          return (
            <li key={key} className={isOpen ? 'is-open' : undefined}>
              <button
                type="button"
                className="services__row"
                aria-expanded={isOpen}
                aria-controls={panel}
                onClick={() => setOpen(isOpen ? null : key)}
              >
                <span>{s.title}</span>
                <ChevronIcon className="services__chev" />
              </button>
              <div id={panel} className="services__detail" hidden={!isOpen}>
                {s.image && <img src={s.image} alt="" loading="lazy" width="600" height="400" />}
                <p>{s.body}</p>
                <a
                  className="link-wa"
                  href={whatsappLink(content.contact.whatsapp, `Hola, quiero información sobre ${s.title} (${cat.name}).`)}
                  target="_blank"
                  rel="noopener"
                  onClick={() => trackContact({ channel: 'whatsapp', service: s.title })}
                >
                  <WhatsAppIcon />
                  Preguntar por {s.title}
                </a>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
