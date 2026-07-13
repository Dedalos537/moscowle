/** Fecha local YYYY-MM-DD (evita desfase de toISOString/UTC). */
export function toLocalDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

/**
 * Extract HH:MM directly from an ISO string without timezone conversion.
 * Backend returns local times with offset (e.g. "2026-07-13T13:05:00-05:00").
 * This parses the string directly to avoid browser timezone re-conversion.
 */
export function timeFromISO(iso: string | null | undefined): string {
  if (!iso) return '';
  const m = iso.match(/T(\d{2}):(\d{2})/);
  return m ? `${m[1]}:${m[2]}` : '';
}

/**
 * Extract YYYY-MM-DD directly from an ISO string without timezone conversion.
 */
export function dateFromISO(iso: string | null | undefined): string {
  if (!iso) return '';
  const m = iso.match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}-${m[3]}` : '';
}
