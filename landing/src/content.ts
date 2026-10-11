import { useEffect, useState } from 'react';
import fallback from '../../app/data/landing_default.json';
import { API_URL } from './api';

export interface Service {
  title: string;
  body: string;
  category: string;
  image: string;
}

export interface Content {
  seo: { title: string; description: string };
  brand: { name: string; short: string };
  contact: {
    whatsapp: string;
    phone: string;
    email: string;
    address: string;
    city: string;
    maps_url: string;
    phone_hours: string;
    hours: { days: string; time: string }[];
    hours_note: string;
  };
  hero: { title: string; highlight: string; subtitle: string; cta_primary: string; cta_secondary: string };
  stats: { value: string; label: string }[];
  evaluation: {
    title: string;
    subtitle: string;
    steps: { title: string; body: string }[];
    whatsapp_message: string;
  };
  services_intro: { title: string; subtitle: string };
  services: Service[];
  about: { title: string; body: string; values: { title: string; body: string }[] };
  testimonials_intro: { title: string; subtitle: string };
  testimonials: { quote: string; author: string; relation: string }[];
  faq: { q: string; a: string }[];
}

export const DEFAULT_CONTENT = fallback as Content;

const CACHE_KEY = 'cjp-landing-content';

function cached(): Content | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Content) : null;
  } catch {
    return null;
  }
}

/** Pinta al instante (última versión vista o la de respaldo) y se actualiza con la publicada en el admin. */
export function useContent(): Content {
  const [content, setContent] = useState<Content>(() => cached() ?? DEFAULT_CONTENT);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch(`${API_URL}/api/landing/content`, { signal: ctrl.signal })
      .then((r) => (r.ok ? r.json() : null))
      .then((body: { content?: Content } | null) => {
        if (!body?.content) return;
        setContent(body.content);
        try {
          localStorage.setItem(CACHE_KEY, JSON.stringify(body.content));
        } catch {
          /* sin almacenamiento: se queda la versión en memoria */
        }
      })
      .catch(() => {
        /* sin conexión: se mantiene el contenido de respaldo */
      });
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    document.title = content.seo.title;
    document.querySelector('meta[name="description"]')?.setAttribute('content', content.seo.description);
  }, [content.seo]);

  return content;
}

export function whatsappLink(number: string, message: string): string {
  return `https://wa.me/${number}?text=${encodeURIComponent(message)}`;
}

export function telLink(phone: string): string {
  return `tel:${phone.replace(/[^\d+]/g, '')}`;
}
