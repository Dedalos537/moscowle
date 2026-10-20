/**
 * Tipos de notificación y formas de mostrarlas (PRP 011 · E2). El backend manda `kind` + `presentation` en cada
 * evento; este archivo da los tipos de TypeScript y el comportamiento por defecto si un evento llega sin ellos.
 */
export type Presentation = 'badge' | 'toast' | 'snackbar' | 'banner' | 'modal' | 'push';

export interface NotificationAction {
  label: string;
  link: string | null;
}

export interface NotificationEvent {
  id: number;
  title: string;
  message: string;
  category: string;
  priority: 'low' | 'normal' | 'high' | 'urgent' | string;
  type?: string;
  icon?: string | null;
  link?: string | null;
  kind?: string;
  presentation?: Presentation[];
  action?: NotificationAction | null;
  push_when?: 'hidden' | 'always';
  payload?: Record<string, string | number | boolean | null>;
  group_count?: number;
  unread_count?: number;
}

/** Tono visual por prioridad/tipo (lo usan banner, snackbar y modal). */
export type NoticeTone = 'info' | 'success' | 'warning' | 'danger';

export function toneOf(ev: NotificationEvent): NoticeTone {
  if (ev.payload?.['resolved']) return 'success';
  if (ev.priority === 'urgent' || ev.type === 'error') return 'danger';
  if (ev.priority === 'high' || ev.type === 'warning') return 'warning';
  if (ev.type === 'success') return 'success';
  return 'info';
}

/** Si el backend todavía no manda `presentation` (o es un evento viejo), se decide por prioridad. */
export function presentationOf(ev: NotificationEvent): Presentation[] {
  if (ev.presentation?.length) return ev.presentation;
  const out: Presentation[] = ['badge'];
  if (ev.priority === 'urgent') out.push('banner', 'push');
  else if (ev.priority === 'high') out.push('toast');
  return out;
}
