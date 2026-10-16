import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { AuthService } from './auth.service';
import { GlobalSettingsService, type PersonDisplay } from './global-settings.service';

export interface Person {
  id: number;
  name: string;
  code: string;
  email: string;
  role: string;
}

/** Referencia a una persona tal como llega en cada módulo: a veces solo el nombre, a veces el id. */
export interface PersonRef {
  id?: number | null;
  name?: string | null;
  code?: string | null;
  email?: string | null;
}

const STAFF = new Set(['admin', 'supervisor', 'terapista', 'terapeuta']);

/** Minúsculas y sin tildes, para buscar «Jose» y encontrar «José». */
export function normalize(text: string | null | undefined): string {
  return (text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

/**
 * Directorio de personas (nombre, código de acceso y correo) para mostrarlas como «Nombre · CÓDIGO» o solo
 * «CÓDIGO» en todo el sistema, y buscarlas por nombre, código o correo.
 *
 * Qué modo aplica: si un administrador activó «Solo códigos para todo el centro», todo el personal ve códigos;
 * si no, cada quien usa su preferencia personal. Los pacientes siempre ven nombres (su terapeuta, etc.).
 * El directorio viene de `/api/people/directory`, ya filtrado por rol en el servidor.
 */
@Injectable({ providedIn: 'root' })
export class PeopleService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private settings = inject(GlobalSettingsService);

  readonly people = signal<Person[]>([]);
  /** Ajuste del centro: si está activo, todo el personal ve solo códigos. */
  readonly centerCodeOnly = signal(false);
  private readonly role = signal('');
  readonly mode = computed<PersonDisplay>(() => {
    if (!STAFF.has(this.role())) return 'name_code';
    return this.centerCodeOnly() ? 'code' : this.settings.personDisplay();
  });

  private readonly byId = computed(() => new Map(this.people().map((p) => [p.id, p])));
  /** Nombres repetidos quedan como `null`: no se adivina a quién se refieren. */
  private readonly byName = computed(() => {
    const map = new Map<string, Person | null>();
    for (const p of this.people()) {
      const key = normalize(p.name);
      if (key) map.set(key, map.has(key) ? null : p);
    }
    return map;
  });

  private loadedFor: number | null = null;

  constructor() {
    this.auth.currentUser$.subscribe((user) => {
      const id: number | null = user?.id ?? null;
      const role: string = user?.role ?? user?.user?.role ?? '';
      this.role.set(role);
      if (id === null) {
        this.loadedFor = null;
        this.people.set([]);
        this.centerCodeOnly.set(false);
      } else if (id !== this.loadedFor && STAFF.has(role)) {
        this.loadedFor = id;
        this.reload();
      }
    });
    // Si un administrador cambia el ajuste del centro, las demás pantallas lo toman al volver a la pestaña.
    if (typeof window !== 'undefined') {
      window.addEventListener('focus', () => {
        if (this.loadedFor !== null) this.loadCenterSetting();
      });
    }
  }

  /** Vuelve a pedir el directorio y el ajuste del centro (p. ej. tras crear un usuario o cambiar un código). */
  reload(): void {
    this.loadCenterSetting();
    this.http.get<{ success: boolean; people: Person[] }>('/api/people/directory').subscribe({
      next: (res) => this.people.set(res.people ?? []),
      error: () => {},
    });
  }

  private loadCenterSetting(): void {
    this.http.get<{ center_code_only: boolean }>('/api/people/settings').subscribe({
      next: (res) => this.centerCodeOnly.set(!!res.center_code_only),
      error: () => {},
    });
  }

  /** Solo admin: activa o quita «solo códigos» para todo el personal del centro. */
  setCenterCodeOnly(on: boolean): void {
    const previous = this.centerCodeOnly();
    this.centerCodeOnly.set(on);
    this.http.put<{ center_code_only: boolean }>('/api/people/settings', { center_code_only: on }).subscribe({
      next: (res) => this.centerCodeOnly.set(!!res.center_code_only),
      error: () => this.centerCodeOnly.set(previous),
    });
  }

  find(ref: PersonRef): Person | null {
    if (ref.id != null) {
      const p = this.byId().get(Number(ref.id));
      if (p) return p;
    }
    return ref.name ? (this.byName().get(normalize(ref.name)) ?? null) : null;
  }

  /** «Nombre · CÓDIGO» o solo «CÓDIGO» según la preferencia; sin código conocido, el nombre. */
  label(ref: PersonRef, fallback = '—'): string {
    const person = this.find(ref);
    const name = ref.name || person?.name || '';
    const code = ref.code || person?.code || '';
    if (this.mode() === 'code') return code || name || fallback;
    if (code && name) return `${name} · ${code}`;
    return name || code || fallback;
  }

  /** Iniciales para avatares: con «solo código» no se deja ver el nombre. */
  initials(ref: PersonRef): string {
    const text = this.mode() === 'code' ? this.label(ref, '?') : ref.name || this.find(ref)?.name || '?';
    const parts = text.replace(/[·]/g, ' ').trim().split(/\s+/).filter(Boolean);
    return ((parts[0]?.[0] ?? '?') + (parts[1]?.[0] ?? '')).toUpperCase();
  }

  /** Opción para un `<app-select>`: muestra la etiqueta según el modo y busca por nombre, código y correo. */
  option(id: number, name: string | null | undefined, email?: string | null): { value: number; label: string; keywords: string } {
    const person = this.find({ id, name });
    const keywords = [name, person?.name, person?.code, email, person?.email].filter(Boolean).join(' ');
    return { value: id, label: this.label({ id, name }), keywords };
  }

  /** ¿La búsqueda coincide con el nombre, el código o el correo de la persona? */
  matches(query: string | null | undefined, ref: PersonRef): boolean {
    const q = normalize(query);
    if (!q) return true;
    const person = this.find(ref);
    return [ref.name, ref.code, ref.email, person?.name, person?.code, person?.email].some((v) => normalize(v).includes(q));
  }
}
