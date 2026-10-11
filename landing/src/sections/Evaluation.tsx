import { useRef } from 'react';
import type { Content } from '../content';
import { useScene } from '../three/useScene';

/** El recorrido de la evaluación: el bloque avanza por las estaciones al ritmo del scroll y el paso activo se marca. */
export function Evaluation({ content }: { content: Content }) {
  const section = useRef<HTMLElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const { steps } = content.evaluation;
  const { failed, progress } = useScene('path', canvas, section, { progress: 'section', count: steps.length });
  const active = Math.min(steps.length - 1, Math.floor(progress * steps.length * 0.999));

  return (
    <section ref={section} id="evaluacion" className="journey" aria-labelledby="journey-title">
      <div className="journey__head">
        <h2 id="journey-title">{content.evaluation.title}</h2>
        <p>{content.evaluation.subtitle}</p>
      </div>
      <div className="journey__body">
        <div className="journey__stage" aria-hidden="true">
          {!failed && <canvas ref={canvas} className="journey__canvas" />}
        </div>
        <ol className="journey__steps">
          {steps.map((s, i) => (
            <li key={i} className={i <= active ? 'is-reached' : undefined} aria-current={i === active ? 'step' : undefined}>
              <span className="journey__dot" aria-hidden="true" />
              <h3>{s.title}</h3>
              <p>{s.body}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
