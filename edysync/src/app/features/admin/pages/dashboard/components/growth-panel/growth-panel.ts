import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { CenterDashboard } from '../../../../../../core/models/center-dashboard';
import { ScorecardKpi } from '../../../../../../core/models/sede';
import { delta, fmtShort, fmtValue, monthLabel, statusLabel, targetLabel } from '../../../sedes/kpi-format';

type MetricKey = 'revenue' | 'collection' | 'overdue' | 'active_patients' | 'retention' | 'attendance' | 'growth';

interface Metric {
  key: MetricKey;
  label: string;
  value: string;
  delta: { text: string; tone: string };
  status: string;
  statusText: string;
  question: string;
  link: { to: string; label: string };
}

const W = 640;
const H = 248;
const PAD = { t: 28, r: 12, b: 34, l: 12 };

/** Qué responde cada indicador: así el admin sabe para qué mirarlo. */
const QUESTIONS: Record<MetricKey, string> = {
  revenue: '¿Cuánto entró de verdad este periodo?',
  collection: '¿Se pagan las cuotas a tiempo?',
  overdue: '¿Cuánta deuda vencida arrastramos?',
  active_patients: '¿A cuántos pacientes atendimos?',
  retention: '¿Los pacientes siguen viniendo?',
  attendance: '¿Vienen a las sesiones agendadas?',
  growth: '¿Entran más pacientes de los que se van?',
};

const LINKS: Record<MetricKey, { to: string; label: string }> = {
  revenue: { to: '/admin/finanzas', label: 'Ver en Finanzas' },
  collection: { to: '/admin/finanzas', label: 'Ver cuotas en Finanzas' },
  overdue: { to: '/admin/payments', label: 'Ver deudores en Pagos' },
  active_patients: { to: '/admin/reports', label: 'Ver en Reportes' },
  retention: { to: '/admin/reports', label: 'Ver en Reportes' },
  attendance: { to: '/admin/sessions', label: 'Ver la agenda' },
  growth: { to: '/admin/users', label: 'Ver pacientes' },
};

/**
 * Crecimiento: cada indicador es una pestaña que cambia el gráfico de 6 meses (con meta y comparación).
 * El gráfico se recorre con el teclado: cada mes es un punto enfocable con su valor.
 */
@Component({
  selector: 'app-growth-panel',
  standalone: true,
  imports: [FontAwesomeModule, RouterLink],
  templateUrl: './growth-panel.html',
  styleUrl: './growth-panel.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GrowthPanel {
  data = input.required<CenterDashboard>();

  readonly W = W;
  readonly H = H;
  readonly PAD = PAD;
  readonly selected = signal<MetricKey>('revenue');
  readonly hover = signal<number | null>(null);

  private readonly kpis = computed(() => new Map(this.data().pulse.map((k) => [k.key, k])));

  readonly metrics = computed<Metric[]>(() => {
    const k = this.kpis();
    const flow = this.data().flow;
    const now = flow[flow.length - 1];
    const before = flow[flow.length - 2];
    const growthDelta =
      now && before
        ? now.net === before.net
          ? { text: 'Igual que el mes pasado', tone: 'same' }
          : { text: `${now.net > before.net ? '↑' : '↓'} ${Math.abs(now.net - before.net)} vs. mes pasado`, tone: now.net > before.net ? 'better' : 'worse' }
        : { text: 'Sin comparación', tone: 'none' };
    const fromKpi = (key: Exclude<MetricKey, 'growth'>, label?: string): Metric | null => {
      const kpi = k.get(key);
      if (!kpi) return null;
      return {
        key,
        label: label ?? kpi.label,
        value: fmtValue(kpi.value, kpi.unit),
        delta: delta(kpi),
        status: kpi.status,
        statusText: statusLabel(kpi),
        question: QUESTIONS[key],
        link: LINKS[key],
      };
    };
    const list = [
      fromKpi('revenue'),
      fromKpi('collection', 'Cobranza'),
      fromKpi('active_patients'),
      {
        key: 'growth' as const,
        label: 'Crecimiento neto',
        value: now ? `${now.net > 0 ? '+' : ''}${now.net}` : 'Sin datos',
        delta: growthDelta,
        status: now ? (now.net > 0 ? 'good' : now.net < 0 ? 'bad' : 'warn') : 'none',
        statusText: now ? `${now.new} ${now.new === 1 ? 'alta' : 'altas'} · ${now.left} ${now.left === 1 ? 'baja' : 'bajas'} este mes` : '',
        question: QUESTIONS.growth,
        link: LINKS.growth,
      },
      fromKpi('retention'),
      fromKpi('attendance'),
      fromKpi('overdue'),
    ];
    return list.filter((m): m is Metric => !!m);
  });

  readonly current = computed(() => this.metrics().find((m) => m.key === this.selected()) ?? this.metrics()[0]);
  readonly kpi = computed<ScorecardKpi | null>(() => (this.selected() === 'growth' ? null : (this.kpis().get(this.selected()) ?? null)));

  /** Barras de una serie de 6 meses, con línea de meta si existe. */
  readonly bars = computed(() => {
    const kpi = this.kpi();
    if (!kpi) return null;
    const months = this.data().months;
    const values = kpi.trend;
    const max = Math.max(...values.map((v) => v ?? 0), kpi.target ?? 0, 1) * 1.12;
    const plotW = W - PAD.l - PAD.r;
    const plotH = H - PAD.t - PAD.b;
    const step = plotW / values.length;
    const bw = Math.min(56, step * 0.56);
    return {
      targetY: kpi.target != null ? PAD.t + plotH - (kpi.target / max) * plotH : null,
      targetText: kpi.target != null ? targetLabel(kpi) : null,
      items: values.map((v, i) => {
        const h = v == null ? 0 : Math.max(2, (v / max) * plotH);
        const x = PAD.l + step * i + (step - bw) / 2;
        const y = PAD.t + plotH - h;
        return {
          x,
          y,
          w: bw,
          h,
          cx: x + bw / 2,
          empty: v == null,
          current: i === values.length - 1,
          month: monthLabel(months[i]),
          value: fmtShort(v, kpi.unit),
          full: `${monthLabel(months[i])}: ${v == null ? 'sin datos' : fmtValue(v, kpi.unit)}`,
          path: roundedTop(x, y, bw, h, Math.min(5, h)),
        };
      }),
    };
  });

  /** Altas arriba y bajas abajo del eje: el crecimiento neto se lee de un vistazo. */
  readonly flowBars = computed(() => {
    if (this.selected() !== 'growth') return null;
    const flow = this.data().flow;
    const max = Math.max(...flow.map((m) => Math.max(m.new, m.left)), 1) * 1.15;
    const plotW = W - PAD.l - PAD.r;
    const half = (H - PAD.t - PAD.b) / 2;
    const mid = PAD.t + half;
    const step = plotW / flow.length;
    const bw = Math.min(26, step * 0.3);
    return {
      mid,
      items: flow.map((m, i) => {
        const nh = (m.new / max) * half;
        const lh = (m.left / max) * half;
        const x = PAD.l + step * i + step / 2;
        return {
          cx: x,
          newPath: m.new ? roundedTop(x - bw - 1, mid - nh, bw, nh, Math.min(4, nh)) : null,
          leftPath: m.left ? roundedBottom(x + 1, mid, bw, lh, Math.min(4, lh)) : null,
          newY: mid - nh,
          leftY: mid + lh,
          month: monthLabel(m.month),
          current: i === flow.length - 1,
          m,
          full: `${monthLabel(m.month)}: ${m.new} ${m.new === 1 ? 'alta' : 'altas'}, ${m.left} ${m.left === 1 ? 'baja' : 'bajas'}, neto ${m.net > 0 ? '+' : ''}${m.net}`,
        };
      }),
    };
  });

  select(key: MetricKey) {
    this.selected.set(key);
    this.hover.set(null);
  }

  /** Flechas izquierda/derecha entre pestañas (patrón de tabs ARIA). */
  onTabKey(event: KeyboardEvent, index: number) {
    const list = this.metrics();
    const next = event.key === 'ArrowRight' || event.key === 'ArrowDown' ? index + 1 : event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? index - 1 : null;
    if (next === null) return;
    event.preventDefault();
    const target = list[(next + list.length) % list.length];
    this.select(target.key);
    (document.getElementById('gp-tab-' + target.key) as HTMLElement | null)?.focus();
  }
}

function roundedTop(x: number, y: number, w: number, h: number, r: number): string {
  if (h <= 0) return '';
  return `M${x},${y + h} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${y + h} Z`;
}

function roundedBottom(x: number, y: number, w: number, h: number, r: number): string {
  if (h <= 0) return '';
  return `M${x},${y} V${y + h - r} Q${x},${y + h} ${x + r},${y + h} H${x + w - r} Q${x + w},${y + h} ${x + w},${y + h - r} V${y} Z`;
}
