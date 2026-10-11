import { useRef } from 'react';
import { trackContact } from '../api';
import { type Content, telLink } from '../content';
import { FlatBlocks, PhoneIcon } from '../icons';
import { useScene } from '../three/useScene';

export function Hero({ content }: { content: Content }) {
  const section = useRef<HTMLElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const { failed } = useScene('hero', canvas, section, { progress: 'leave', pointer: true });
  const { hero, contact } = content;

  return (
    <section ref={section} className="hero" aria-labelledby="hero-title">
      <div className="hero__stage" aria-hidden="true">
        {failed ? <FlatBlocks className="hero__flat" /> : <canvas ref={canvas} className="hero__canvas" />}
      </div>
      <div className="hero__copy">
        <h1 id="hero-title" className="hero__title">
          {hero.title}
          {hero.highlight && <span className="hero__highlight">{hero.highlight}</span>}
        </h1>
        <p className="hero__lead">{hero.subtitle}</p>
        <div className="hero__actions">
          <a className="btn btn--lime" href="#agendar">
            {hero.cta_primary}
          </a>
          <a
            className="btn btn--ghost-light"
            href={telLink(contact.phone)}
            onClick={() => trackContact({ channel: 'call' })}
          >
            <PhoneIcon />
            <span>
              Llamar <span className="nowrap">{contact.phone.replace(/^\+51\s*/, '')}</span>
            </span>
          </a>
        </div>
        {hero.cta_secondary && (
          <a className="hero__more" href="#terapias">
            {hero.cta_secondary}
          </a>
        )}
      </div>
    </section>
  );
}
