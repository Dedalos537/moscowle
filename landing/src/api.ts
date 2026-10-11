/** Conexión con la API de comunicaciones de la landing (/api/landing), aparte del resto de la plataforma. */

export const API_URL = (import.meta.env.VITE_API_URL || 'https://api-centrojuanpabloii.online').replace(/\/+$/, '');

export type Channel = 'form' | 'whatsapp' | 'call';
export type PreferredTime = 'manana' | 'tarde' | 'cualquiera';

export interface LeadPayload {
  channel: Channel;
  name?: string;
  phone?: string;
  email?: string;
  patient_age?: string;
  service?: string;
  preferred_time?: PreferredTime;
  message?: string;
  website?: string;
}

function source(): string | undefined {
  const params = new URLSearchParams(location.search);
  const utm = ['utm_source', 'utm_medium', 'utm_campaign']
    .map((k) => params.get(k))
    .filter(Boolean)
    .join(' / ');
  if (utm) return utm.slice(0, 200);
  try {
    const ref = document.referrer ? new URL(document.referrer).hostname : '';
    return ref && ref !== location.hostname ? ref : undefined;
  } catch {
    return undefined;
  }
}

/** Registra que alguien abrió WhatsApp o pulsó «Llamar». No espera respuesta: el enlace se abre igual. */
export function trackContact(payload: LeadPayload): void {
  try {
    fetch(`${API_URL}/api/landing/leads`, {
      method: 'POST',
      keepalive: true,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, source: source() }),
    }).catch(() => undefined);
  } catch {
    /* el contacto nunca depende del registro */
  }
}

export class LeadError extends Error {
  constructor(
    message: string,
    public field?: string,
  ) {
    super(message);
  }
}

/** Solicitud «que me llamen»: aquí sí se espera la respuesta para confirmar o mostrar el error. */
export async function sendLead(payload: LeadPayload): Promise<void> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/landing/leads`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...payload, source: source() }),
    });
  } catch {
    throw new LeadError('No pudimos enviar tu solicitud. Revisa tu conexión o escríbenos por WhatsApp.');
  }
  if (res.ok) return;
  if (res.status === 429) {
    throw new LeadError('Ya recibimos varias solicitudes desde este equipo. Te llamaremos pronto, o escríbenos por WhatsApp.');
  }
  const body = (await res.json().catch(() => null)) as { error?: string; field?: string } | null;
  throw new LeadError(body?.error || 'No pudimos enviar tu solicitud. Inténtalo de nuevo.', body?.field);
}
