import type { Content } from '../content';
import { BlockGlyph } from '../icons';

const SHAPES = ['circle', 'square', 'triangle', 'rect', 'circle', 'square', 'triangle', 'rect'] as const;

export function About({ content }: { content: Content }) {
  const { about } = content;
  return (
    <section id="nosotros" className="about" aria-labelledby="about-title">
      <div className="about__intro">
        <h2 id="about-title">{about.title}</h2>
        <p>{about.body}</p>
      </div>
      {about.values.length > 0 && (
        <ul className="about__values" aria-label="Nuestros valores">
          {about.values.map((v, i) => (
            <li key={v.title}>
              <BlockGlyph shape={SHAPES[i]} className={`glyph glyph--${SHAPES[i]}`} />
              <div>
                <h3>{v.title}</h3>
                <p>{v.body}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function Testimonials({ content }: { content: Content }) {
  if (!content.testimonials.length) return null;
  return (
    <section className="voices" aria-labelledby="voices-title">
      <div className="section-head">
        <h2 id="voices-title">{content.testimonials_intro.title}</h2>
        {content.testimonials_intro.subtitle && <p>{content.testimonials_intro.subtitle}</p>}
      </div>
      <ul className="voices__list">
        {content.testimonials.map((t) => (
          <li key={t.author}>
            <figure>
              <blockquote>
                <p>{t.quote}</p>
              </blockquote>
              <figcaption>
                <strong>{t.author}</strong>
                {t.relation && <span>{t.relation}</span>}
              </figcaption>
            </figure>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Faq({ content }: { content: Content }) {
  if (!content.faq.length) return null;
  return (
    <section className="faq" aria-labelledby="faq-title">
      <h2 id="faq-title">Preguntas frecuentes</h2>
      <div className="faq__list">
        {content.faq.map((f) => (
          <details key={f.q}>
            <summary>{f.q}</summary>
            <p>{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
