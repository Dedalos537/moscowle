import { trackContact } from '../api';
import { type Content, telLink } from '../content';
import { PhoneIcon } from '../icons';

const logo = `${import.meta.env.BASE_URL}logo.svg`;

export function TopBar({ content }: { content: Content }) {
  return (
    <header className="topbar">
      <a className="topbar__brand" href="#inicio" aria-label={`${content.brand.name}, inicio`}>
        <img src={logo} alt="" width="36" height="36" />
        <span>
          <span className="topbar__pre">Centro de Terapias</span>
          <strong>{content.brand.short}</strong>
        </span>
      </a>
      <nav className="topbar__nav" aria-label="Secciones">
        <a href="#evaluacion">Evaluación</a>
        <a href="#terapias">Terapias</a>
        <a href="#nosotros">Nosotros</a>
        <a href="https://moscowle.centrojuanpabloii.com" rel="noopener">
          Plataforma
        </a>
      </nav>
      <a
        className="topbar__call"
        href={telLink(content.contact.phone)}
        onClick={() => trackContact({ channel: 'call' })}
      >
        <PhoneIcon />
        <span className="topbar__call-label">Llamar</span>
      </a>
    </header>
  );
}
