import type { SVGProps } from 'react';

/** Iconos dibujados para la página: trazo 1.8, puntas redondas, en una retícula de 24. */

type P = SVGProps<SVGSVGElement>;

const base = (props: P) => ({
  width: 24,
  height: 24,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  focusable: false,
  ...props,
});

export const PhoneIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M5 4h3.2l1.6 4-2 1.3a10.5 10.5 0 0 0 6.9 6.9l1.3-2 4 1.6V19a1.8 1.8 0 0 1-1.9 1.8A15.6 15.6 0 0 1 3.2 5.9 1.8 1.8 0 0 1 5 4Z" />
  </svg>
);

/** Marca de WhatsApp (relleno), reconocible al primer vistazo para las familias. */
export const WhatsAppIcon = (p: P) => (
  <svg {...base(p)} fill="currentColor" stroke="none">
    <path d="M12.04 2a9.9 9.9 0 0 0-8.5 15l-1.4 5.1 5.24-1.37A9.9 9.9 0 1 0 12.04 2Zm0 18.1a8.2 8.2 0 0 1-4.18-1.14l-.3-.18-3.1.82.83-3.03-.2-.31a8.22 8.22 0 1 1 6.95 3.84Zm4.5-6.15c-.25-.12-1.46-.72-1.69-.8-.23-.08-.39-.12-.55.12-.17.25-.64.8-.78.97-.14.16-.29.18-.53.06a6.7 6.7 0 0 1-3.32-2.9c-.25-.43.25-.4.72-1.33.08-.16.04-.3-.02-.43-.06-.12-.55-1.33-.76-1.82-.2-.48-.4-.41-.55-.42h-.47a.9.9 0 0 0-.65.3 2.74 2.74 0 0 0-.86 2.04 4.76 4.76 0 0 0 1 2.53 10.9 10.9 0 0 0 4.18 3.7c1.56.67 2.17.73 2.95.62.48-.07 1.46-.6 1.67-1.18.2-.58.2-1.07.14-1.18-.06-.1-.22-.16-.47-.28Z" />
  </svg>
);

export const PinIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M12 21s-6.5-5.7-6.5-11.2a6.5 6.5 0 0 1 13 0C18.5 15.3 12 21 12 21Z" />
    <circle cx="12" cy="9.8" r="2.3" />
  </svg>
);

export const ClockIcon = (p: P) => (
  <svg {...base(p)}>
    <circle cx="12" cy="12" r="8.5" />
    <path d="M12 7.5V12l3 2" />
  </svg>
);

export const MailIcon = (p: P) => (
  <svg {...base(p)}>
    <rect x="3.5" y="5.5" width="17" height="13" rx="2.2" />
    <path d="m4.5 7 7.5 5.6L19.5 7" />
  </svg>
);

export const ArrowIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="M5 12h13M13 6.5 18.5 12 13 17.5" />
  </svg>
);

export const ChevronIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="m6.5 9.5 5.5 5.5 5.5-5.5" />
  </svg>
);

export const CheckIcon = (p: P) => (
  <svg {...base(p)}>
    <path d="m5.5 12.5 4.2 4.2 8.8-9.4" />
  </svg>
);

/** Glifos de bloque lógico: identifican cada categoría con la misma forma que en las escenas 3D. */
export const BlockGlyph = ({ shape, ...p }: P & { shape: 'circle' | 'square' | 'triangle' | 'rect' }) => (
  <svg {...base(p)} fill="currentColor" stroke="none">
    {shape === 'circle' && <circle cx="12" cy="12" r="8" />}
    {shape === 'square' && <rect x="4.5" y="4.5" width="15" height="15" rx="2.2" />}
    {shape === 'triangle' && <path d="M10.6 4.6a1.6 1.6 0 0 1 2.8 0l7.1 12.6a1.6 1.6 0 0 1-1.4 2.4H4.9a1.6 1.6 0 0 1-1.4-2.4Z" />}
    {shape === 'rect' && <rect x="2.5" y="7" width="19" height="10" rx="2" />}
  </svg>
);

/** Versión plana de la nube de bloques para equipos sin WebGL. */
export const FlatBlocks = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 400 300" aria-hidden="true" focusable="false">
    <circle cx="190" cy="140" r="62" fill="#c4d228" />
    <path d="M300 40a10 10 0 0 1 17 0l40 70a10 10 0 0 1-8.5 15h-80a10 10 0 0 1-8.5-15Z" fill="#e25f43" />
    <rect x="44" y="150" width="88" height="88" rx="12" fill="#2f6fb5" transform="rotate(-12 88 194)" />
    <rect x="250" y="190" width="120" height="70" rx="12" fill="#81a141" transform="rotate(8 310 225)" />
    <circle cx="95" cy="70" r="30" fill="#e25f43" />
    <rect x="200" y="235" width="44" height="44" rx="8" fill="#c4d228" transform="rotate(20 222 257)" />
  </svg>
);
