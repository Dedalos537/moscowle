import { type FormEvent, useId, useMemo, useState } from 'react';
import { LeadError, type PreferredTime, sendLead, trackContact } from '../api';
import { type Content, telLink, whatsappLink } from '../content';
import { CheckIcon, ClockIcon, MailIcon, PhoneIcon, PinIcon, WhatsAppIcon } from '../icons';

const TIMES: { value: PreferredTime; label: string }[] = [
  { value: 'manana', label: 'Mañana' },
  { value: 'tarde', label: 'Tarde' },
  { value: 'cualquiera', label: 'Cualquiera' },
];

const UNSURE = 'Aún no lo sé, quiero orientación';

/** «De Lenguaje» → «Lenguaje»: el nombre del área tal como lo diría una familia. */
function areaName(title: string) {
  return title.replace(/^De\s+/i, '').replace(/\s+Virtual$/i, ' (virtual)');
}

/**
 * Agendar la evaluación: lo primordial de la página. Tres caminos con los mismos datos: WhatsApp (el mensaje se arma
 * solo con lo que la familia llenó), llamada directa, o dejar el teléfono para que el centro llame.
 */
export function Booking({ content }: { content: Content }) {
  const { contact, evaluation } = content;
  const id = useId();
  const areas = useMemo(() => {
    const seen = new Set<string>();
    const list: string[] = [];
    for (const s of content.services) {
      const name = areaName(s.title);
      if (!seen.has(name.toLowerCase())) {
        seen.add(name.toLowerCase());
        list.push(name);
      }
    }
    return list;
  }, [content.services]);

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [age, setAge] = useState('');
  const [area, setArea] = useState('');
  const [time, setTime] = useState<PreferredTime | ''>('');
  const [trap, setTrap] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<{ message: string; field?: string } | null>(null);
  const [sent, setSent] = useState(false);

  const message = useMemo(() => {
    const lines = [evaluation.whatsapp_message];
    if (name.trim()) lines.push(`Mi nombre es ${name.trim()}.`);
    if (age.trim()) lines.push(`Edad de mi hijo/a: ${age.trim()}.`);
    if (area && area !== UNSURE) lines.push(`Me preocupa: ${area}.`);
    if (area === UNSURE) lines.push('Aún no sé qué terapia necesita; quisiera orientación.');
    if (time === 'manana' || time === 'tarde') lines.push(`Prefiero un horario de ${time === 'manana' ? 'mañana' : 'tarde'}.`);
    return lines.join('\n');
  }, [evaluation.whatsapp_message, name, age, area, time]);

  const details = () => ({
    name: name.trim() || undefined,
    phone: phone.trim() || undefined,
    patient_age: age.trim() || undefined,
    service: area || undefined,
    preferred_time: time || undefined,
    website: trap || undefined,
  });

  const requestCall = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return setError({ message: 'Escribe tu nombre para saber a quién llamar.', field: 'name' });
    if (phone.replace(/\D/g, '').length < 6) {
      return setError({ message: 'Escribe un número de celular o teléfono para llamarte.', field: 'phone' });
    }
    setError(null);
    setSending(true);
    try {
      await sendLead({ channel: 'form', ...details(), message: message });
      setSent(true);
    } catch (err) {
      setError(err instanceof LeadError ? { message: err.message, field: err.field } : { message: 'No pudimos enviar tu solicitud.' });
    } finally {
      setSending(false);
    }
  };

  const fieldError = (f: string) => (error?.field === f ? `${id}-error` : undefined);

  return (
    <section id="agendar" className="booking" aria-labelledby="booking-title">
      <div className="booking__copy">
        <h2 id="booking-title">Agenda la evaluación inicial</h2>
        <p>Cuéntanos un poco y elige cómo prefieres hablar con nosotros. Te respondemos el mismo día en horario de atención.</p>
        <ul className="booking__facts">
          <li>
            <PhoneIcon />
            <div>
              <a href={telLink(contact.phone)} onClick={() => trackContact({ channel: 'call' })}>
                {contact.phone}
              </a>
              {contact.phone_hours && <span>{contact.phone_hours}</span>}
            </div>
          </li>
          <li>
            <PinIcon />
            <div>
              {contact.maps_url ? (
                <a href={contact.maps_url} target="_blank" rel="noopener">
                  {contact.address}
                </a>
              ) : (
                <span className="booking__strong">{contact.address}</span>
              )}
              <span>{contact.city}</span>
            </div>
          </li>
          <li>
            <ClockIcon />
            <div>
              {contact.hours.map((h) => (
                <span key={h.days} className="booking__strong">
                  {h.days}: {h.time}
                </span>
              ))}
              {contact.hours_note && <span>{contact.hours_note}</span>}
            </div>
          </li>
          {contact.email && (
            <li>
              <MailIcon />
              <div>
                <a href={`mailto:${contact.email}`}>{contact.email}</a>
              </div>
            </li>
          )}
        </ul>
      </div>

      <div className="booking__panel">
        {sent ? (
          <div className="booking__done" role="status">
            <span className="booking__done-mark">
              <CheckIcon />
            </span>
            <h3>Listo, {name.trim().split(' ')[0]}.</h3>
            <p>
              Recibimos tu solicitud. Te llamaremos al {phone.trim()}
              {time === 'manana' ? ' en la mañana' : time === 'tarde' ? ' en la tarde' : ''} para coordinar la evaluación.
            </p>
            <a
              className="btn btn--wa"
              href={whatsappLink(contact.whatsapp, message)}
              target="_blank"
              rel="noopener"
              onClick={() => trackContact({ channel: 'whatsapp', ...details() })}
            >
              <WhatsAppIcon />
              ¿Prefieres escribirnos ya? WhatsApp
            </a>
          </div>
        ) : (
          <form onSubmit={requestCall} noValidate>
            <div className="field-row">
              <label className="field">
                <span>Tu nombre</span>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  autoComplete="name"
                  maxLength={120}
                  aria-invalid={error?.field === 'name' || undefined}
                  aria-describedby={fieldError('name')}
                />
              </label>
              <label className="field">
                <span>Edad de tu hijo/a</span>
                <input
                  value={age}
                  onChange={(e) => setAge(e.target.value)}
                  placeholder="Ej. 5 años"
                  maxLength={30}
                />
              </label>
            </div>
            <label className="field">
              <span>¿Qué te preocupa?</span>
              <select value={area} onChange={(e) => setArea(e.target.value)}>
                <option value="">Elige un área (opcional)</option>
                {areas.map((a) => (
                  <option key={a} value={a}>
                    {a}
                  </option>
                ))}
                <option value={UNSURE}>{UNSURE}</option>
              </select>
            </label>
            <fieldset className="field">
              <legend>Horario que te acomoda</legend>
              <div className="segmented">
                {TIMES.map((t) => (
                  <label key={t.value}>
                    <input
                      type="radio"
                      name={`${id}-time`}
                      value={t.value}
                      checked={time === t.value}
                      onChange={() => setTime(t.value)}
                    />
                    <span>{t.label}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <div className="booking__primary">
              <a
                className="btn btn--wa btn--block"
                href={whatsappLink(contact.whatsapp, message)}
                target="_blank"
                rel="noopener"
                onClick={() => trackContact({ channel: 'whatsapp', ...details() })}
              >
                <WhatsAppIcon />
                Agendar por WhatsApp
              </a>
              <a
                className="btn btn--outline btn--block"
                href={telLink(contact.phone)}
                onClick={() => trackContact({ channel: 'call', ...details() })}
              >
                <PhoneIcon />
                Llamar ahora
              </a>
            </div>

            <div className="booking__callback">
              <p className="booking__or">
                <span>o deja tu número y te llamamos</span>
              </p>
              <label className="field">
                <span>Tu celular</span>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="9XX XXX XXX"
                  maxLength={30}
                  aria-invalid={error?.field === 'phone' || undefined}
                  aria-describedby={fieldError('phone')}
                />
              </label>
              {/* Trampa para bots: invisible y fuera del orden de tabulación. */}
              <label className="trap" aria-hidden="true">
                Sitio web
                <input tabIndex={-1} autoComplete="off" value={trap} onChange={(e) => setTrap(e.target.value)} />
              </label>
              {error && (
                <p id={`${id}-error`} className="form-error" role="alert">
                  {error.message}
                </p>
              )}
              <button className="btn btn--dark btn--block" type="submit" disabled={sending}>
                {sending ? 'Enviando…' : 'Que me llamen'}
              </button>
            </div>
          </form>
        )}
      </div>
    </section>
  );
}
