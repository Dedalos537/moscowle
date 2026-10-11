import { useEffect, useState } from 'react';
import { trackContact } from '../api';
import { type Content, telLink, whatsappLink } from '../content';
import { PhoneIcon, WhatsAppIcon } from '../icons';

export function Footer({ content }: { content: Content }) {
  const year = new Date().getFullYear();
  return (
    <footer className="footer">
      <div>
        <strong>{content.brand.name}</strong>
        <p>
          {content.contact.address}, {content.contact.city}
        </p>
      </div>
      <nav aria-label="Enlaces">
        <a href="#evaluacion">Evaluación</a>
        <a href="#terapias">Terapias</a>
        <a href="#nosotros">Nosotros</a>
        <a href="#agendar">Agendar</a>
        <a href="https://moscowle.centrojuanpabloii.com" rel="noopener">
          Plataforma para familias y terapeutas
        </a>
      </nav>
      <p className="footer__legal">
        © {year} {content.brand.name}
      </p>
    </footer>
  );
}

/** Barra fija en el celular con los dos caminos de contacto; aparece cuando el hero ya no está a la vista. */
export function MobileBar({ content }: { content: Content }) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    const hero = document.querySelector('.hero');
    const booking = document.getElementById('agendar');
    if (!hero) return;
    let heroVisible = true;
    let bookingVisible = false;
    const update = () => setShown(!heroVisible && !bookingVisible);
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.target === hero) heroVisible = e.isIntersecting;
        else bookingVisible = e.isIntersecting;
      }
      update();
    });
    io.observe(hero);
    if (booking) io.observe(booking);
    return () => io.disconnect();
  }, []);

  return (
    <div className={`mobilebar${shown ? ' is-shown' : ''}`} aria-hidden={!shown}>
      <a
        className="mobilebar__call"
        href={telLink(content.contact.phone)}
        tabIndex={shown ? 0 : -1}
        onClick={() => trackContact({ channel: 'call' })}
      >
        <PhoneIcon />
        Llamar
      </a>
      <a
        className="mobilebar__wa"
        href={whatsappLink(content.contact.whatsapp, content.evaluation.whatsapp_message)}
        target="_blank"
        rel="noopener"
        tabIndex={shown ? 0 : -1}
        onClick={() => trackContact({ channel: 'whatsapp' })}
      >
        <WhatsAppIcon />
        WhatsApp
      </a>
    </div>
  );
}
