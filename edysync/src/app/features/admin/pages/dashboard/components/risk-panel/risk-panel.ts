import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { CenterDashboard, RiskItem, RiskKind } from '../../../../../../core/models/center-dashboard';
import { PeopleService } from '../../../../../../core/services/people.service';
import { PersonLabelPipe } from '../../../../../../shared/pipes/person-label.pipe';

const KINDS: { kind: RiskKind; label: string; icon: IconProp }[] = [
  { kind: 'debt', label: 'Deuda', icon: ['fas', 'wallet'] },
  { kind: 'absences', label: 'Faltas', icon: ['fas', 'user-clock'] },
  { kind: 'idle', label: 'Sin sesiones', icon: ['fas', 'hourglass-2'] },
  { kind: 'no_schedule', label: 'Sin agenda', icon: ['fas', 'calendar-plus'] },
  { kind: 'plan_ending', label: 'Plan por terminar', icon: ['fas', 'flag'] },
];

/**
 * Continuidad del servicio: pacientes activos con señales concretas de abandono, ordenados por urgencia.
 * Cada fila se abre y ofrece la acción que corresponde (escribir, cobrar, agendar, ver ficha).
 */
@Component({
  selector: 'app-risk-panel',
  standalone: true,
  imports: [DatePipe, RouterLink, FontAwesomeModule, PersonLabelPipe],
  templateUrl: './risk-panel.html',
  styleUrl: './risk-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class RiskPanel {
  data = input.required<CenterDashboard>();
  /** «Registrar pago» abre el panel de cobro del dashboard con este paciente ya elegido. */
  charge = output<{ id: number; name: string; code?: string }>();
  readonly people = inject(PeopleService);

  readonly kinds = KINDS;
  readonly filter = signal<RiskKind | null>(null);
  readonly open = signal<number | null>(null);
  readonly showAll = signal(false);

  readonly items = computed(() => {
    const f = this.filter();
    const list = this.data().risks.items;
    return f ? list.filter((r) => r.reasons.some((x) => x.kind === f)) : list;
  });
  readonly visible = computed(() => (this.showAll() ? this.items() : this.items().slice(0, 8)));
  readonly share = computed(() => {
    const total = this.data().active_patients_now;
    return total ? Math.round((this.data().risks.total / total) * 100) : 0;
  });

  count(kind: RiskKind): number {
    return this.data().risks.by_kind[kind] ?? 0;
  }

  setFilter(kind: RiskKind | null) {
    this.filter.set(this.filter() === kind ? null : kind);
    this.open.set(null);
  }

  toggle(id: number) {
    this.open.set(this.open() === id ? null : id);
  }

  icon(kind: RiskKind): IconProp {
    return KINDS.find((k) => k.kind === kind)?.icon ?? ['fas', 'circle-exclamation'];
  }

  /** Mensaje cordial y concreto para retomar el contacto (sin datos sensibles en el texto). */
  whatsapp(r: RiskItem): string | null {
    if (!r.phone) return null;
    const digits = r.phone.replace(/\D/g, '');
    const phone = digits.length === 9 ? '51' + digits : digits;
    const name = r.patient.name.split(' ')[0] || '';
    const kinds = new Set(r.reasons.map((x) => x.kind));
    const text = kinds.has('debt')
      ? `Hola ${name}, te saludamos del Centro Juan Pablo II. Queríamos ayudarte a ponerte al día con tus cuotas para que la terapia continúe sin interrupciones. ¿Te podemos llamar?`
      : `Hola ${name}, te saludamos del Centro Juan Pablo II. Te extrañamos en las sesiones: ¿agendamos la próxima?`;
    return `https://wa.me/${phone}?text=${encodeURIComponent(text)}`;
  }
}
