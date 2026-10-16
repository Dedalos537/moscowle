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

const STAFF = new Set(['admin', 'supervisor']);

/** Minúsculas y sin tildes, para buscar «Jose» y encontrar «José». */
export function normalize(text: string | null | undefined): string {
  return (text ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
}

/**
 * Directorio de personas (nombre, código de acceso y correo) para mostrarlas según la preferencia
 * «Mostrar personas» y buscarlas por nombre, código o correo en usuarios, finanzas, reportes, mensajes y kanban.
 * Solo se carga para administradores y supervisores; el resto ve los nombres como vienen.
 */
@Injectable({ providedIn: 'root' })
export class PeopleService {
  private http = inject(HttpClient);
  private auth = inject(AuthService);
  private settings = inject(GlobalSettingsService);

  readonly people = signal<Person[]>([]);
  readonly mode = computed<PersonDisplay>(() => this.settings.personDisplay());

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
      if (id === null) {
        this.loadedFor = null;
        this.people.set([]);
      } else if (id !== this.loadedFor && STAFF.has(role)) {
        this.loadedFor = id;
        this.reload();
      }
    });
  }

  /** Vuelve a pedir el directorio (p. ej. tras crear un usuario o cambiar un código). */
  reload(): void {
    this.http.get<{ success: boolean; users: any[] }>('/api/admin/list-users').subscribe({
      next: (res) =>
        this.people.set(
          (res.users ?? []).map((u) => ({
            id: u.id,
            name: u.username ?? '',
            code: u.login_code ?? '',
            email: u.email ?? '',
            role: u.role ?? '',
          })),
        ),
      error: () => {},
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

  /** ¿La búsqueda coincide con el nombre, el código o el correo de la persona? */
  matches(query: string | null | undefined, ref: PersonRef): boolean {
    const q = normalize(query);
    if (!q) return true;
    const person = this.find(ref);
    return [ref.name, ref.code, ref.email, person?.name, person?.code, person?.email].some((v) => normalize(v).includes(q));
  }
}
