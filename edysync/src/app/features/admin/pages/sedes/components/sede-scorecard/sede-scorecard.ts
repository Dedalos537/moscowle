import { ChangeDetectionStrategy, Component, computed, input, output, signal } from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { IconProp } from '@fortawesome/fontawesome-svg-core';
import { PerspectiveKey, Scorecard, ScorecardKpi, SedeScore } from '../../../../../../core/models/sede';
import { DeltaTone, delta, fmtShort, fmtValue, monthLabel, rangeLabel, scoreTone, statusLabel, targetLabel } from '../../kpi-format';

interface KpiRow {
  kpi: ScorecardKpi;
  value: string;
  delta: { text: string; tone: DeltaTone };
  status: string;
  target: string;
  spark: string;
  sparkEnd: { x: number; y: number } | null;
}

interface Bar {
  label: string;
  value: string;
  y: number;
  cx: number;
  hitX: number;
  hitW: number;
  path: string;
  empty: boolean;
  current: boolean;
}

/** Barra con las esquinas superiores redondeadas (4 px) y la base recta sobre el eje. */
function barPath(x: number, y: number, w: number, h: number): string {
  const r = Math.min(4, h, w / 2);
  const b = y + h;
  return `M${x},${b} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${b} Z`;
}

const SW = 72;
const SH = 22;
// Gráfica de detalle (coordenadas del viewBox).
// Del ancho real del panel de detalle (~330 px), para que el texto del SVG se lea a 11-12 px.
const CW = 330;
const CH = 170;
const PAD = { l: 4, r: 4, t: 22, b: 22 };

const ICONS: Record<PerspectiveKey, IconProp> = {
  financial: ['fas', 'sack-dollar'],
  patients: ['fas', 'people-group'],
  process: ['fas', 'gears'],
  growth: ['fas', 'seedling'],
};

/**
 * Balanced Scorecard de una sede (o de todas, en comparación). Los datos llegan ya calculados del backend; aquí
 * solo se agrupan por perspectiva y se dibujan. Seleccionar un indicador abre su detalle: cómo se calcula, los
 * últimos 6 meses frente a la meta y cómo está cada sede.
 */
@Component({
  selector: 'app-sede-scorecard',
  standalone: true,
  imports: [FontAwesomeModule, NgTemplateOutlet],
  templateUrl: './sede-scorecard.html',
  styleUrl: './sede-scorecard.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SedeScorecard {
  data = input.required<Scorecard>();
  /** Sede mostrada; `null` = comparar todas. */
  sedeId = input<number | null>(null);
  sedeChange = output<number | null>();

  readonly selected = signal<string>('revenue');
  readonly hoverBar = signal<number | null>(null);

  readonly CW = CW;
  readonly CH = CH;
  readonly PAD = PAD;
  readonly SW = SW;
  readonly SH = SH;
  readonly icons = ICONS;
  readonly fmtValue = fmtValue;
  readonly scoreTone = scoreTone;

  readonly compare = computed(() => this.sedeId() == null);
  readonly sede = computed<SedeScore | null>(() => this.data().sedes.find((s) => s.id === this.sedeId()) ?? null);
  readonly range = computed(() => rangeLabel(this.data().range));
  readonly prevRange = computed(() => rangeLabel(this.data().previous_range));

  readonly groups = computed(() => {
    const s = this.sede();
    if (!s) return [];
    return this.data().perspectives.map((p) => ({
      key: p.key,
      label: p.label,
      question: p.question,
      score: s.perspectives.find((x) => x.key === p.key)?.score ?? null,
      rows: s.kpis.filter((k) => k.perspective === p.key).map((k) => this.row(k)),
    }));
  });

  /** Matriz de comparación: una fila por indicador, una columna por sede. */
  readonly matrix = computed(() => {
    const d = this.data();
    return d.perspectives.map((p) => ({
      key: p.key,
      label: p.label,
      rows: (d.sedes[0]?.kpis ?? [])
        .filter((k) => k.perspective === p.key)
        .map((k) => ({
          key: k.key,
          label: k.label,
          target: targetLabel(k),
          cells: d.sedes.map((s) => {
            const sk = s.kpis.find((x) => x.key === k.key)!;
            return { sede: s.id, value: fmtValue(sk.value, sk.unit), status: sk.status, statusText: statusLabel(sk) };
          }),
        })),
    }));
  });

  readonly detail = computed(() => {
    const d = this.data();
    const key = this.selected();
    const ref = (this.sede() ?? d.sedes[0])?.kpis.find((k) => k.key === key);
    if (!ref) return null;
    const kpi = this.sede()?.kpis.find((k) => k.key === key) ?? null;

    // Tendencia de 6 meses (solo con una sede elegida).
    let bars: Bar[] = [];
    let targetY: number | null = null;
    let gridY: { y: number; label: string }[] = [];
    if (kpi) {
      const vals = kpi.trend.map((v) => v ?? 0);
      const top = kpi.unit === 'pct' ? 100 : Math.max(1, ...vals, kpi.target ?? 0) * 1.15;
      const y = (v: number) => PAD.t + (1 - v / top) * (CH - PAD.t - PAD.b);
      const slot = (CW - PAD.l - PAD.r) / kpi.trend.length;
      const bw = Math.min(30, slot * 0.56);
      bars = kpi.trend.map((v, i) => {
        const x = PAD.l + slot * i + (slot - bw) / 2;
        const h = Math.max(v ? 2 : 0, CH - PAD.b - y(v ?? 0));
        return {
          label: monthLabel(d.months[i]),
          value: fmtShort(v, kpi.unit),
          y: CH - PAD.b - h,
          cx: x + bw / 2,
          hitX: PAD.l + slot * i,
          hitW: slot,
          path: barPath(x, CH - PAD.b - h, bw, h),
          empty: v == null,
          current: i === kpi.trend.length - 1,
        };
      });
      targetY = kpi.target != null ? y(Math.min(kpi.target, top)) : null;
      gridY = [0, 0.5, 1].map((f) => ({ y: y(top * f), label: fmtShort(top * f, kpi.unit) }));
    }

    // Todas las sedes en el periodo, de mejor a peor según la dirección del indicador.
    const rows = d.sedes.map((s) => ({ id: s.id, name: s.name, k: s.kpis.find((x) => x.key === key)! }));
    const max = Math.max(1, ...rows.map((r) => Math.abs(r.k.value ?? 0)), ref.target ?? 0);
    const sign = ref.direction === 'up' ? -1 : 1;
    const sedes = rows
      .sort((a, b) => (a.k.value == null ? 1 : b.k.value == null ? -1 : sign * (a.k.value - b.k.value)))
      .map((r) => ({
        id: r.id,
        name: r.name,
        value: fmtValue(r.k.value, r.k.unit),
        width: r.k.value == null ? 0 : Math.max(1.5, (Math.abs(r.k.value) / max) * 100),
        status: r.k.status,
        statusText: statusLabel(r.k),
        mine: r.id === this.sedeId(),
      }));
    const targetPct = ref.target != null ? (ref.target / max) * 100 : null;

    return {
      ref,
      kpi,
      row: kpi ? this.row(kpi) : null,
      target: targetLabel(ref),
      bars,
      gridY,
      targetY,
      targetText: ref.target != null ? fmtShort(ref.target, ref.unit) : '',
      chartLabel: `${ref.label} por mes: ${bars.map((b) => `${b.label} ${b.empty ? 'sin datos' : b.value}`).join(', ')}`,
      sedes,
      targetPct,
    };
  });

  select(key: string) {
    this.selected.set(key);
    this.hoverBar.set(null);
  }

  /** Flechas ↑/↓ recorren los indicadores en el orden en que se ven. */
  onKpiKey(ev: KeyboardEvent, key: string) {
    if (ev.key !== 'ArrowDown' && ev.key !== 'ArrowUp') return;
    const keys = (this.sede() ?? this.data().sedes[0])?.kpis.map((k) => k.key) ?? [];
    const next = keys[keys.indexOf(key) + (ev.key === 'ArrowDown' ? 1 : -1)];
    if (!next) return;
    ev.preventDefault();
    this.select(next);
    const host = (ev.currentTarget as HTMLElement).closest('.bsc');
    host?.querySelector<HTMLElement>(`[data-kpi="${next}"]`)?.focus();
  }

  private row(k: ScorecardKpi): KpiRow {
    const vals = k.trend.filter((v): v is number => v != null);
    let spark = '';
    let sparkEnd: { x: number; y: number } | null = null;
    if (vals.length >= 2) {
      const lo = Math.min(...vals);
      const hi = Math.max(...vals);
      const span = hi - lo || 1;
      const step = (SW - 4) / (k.trend.length - 1);
      let pen = 'M';
      k.trend.forEach((v, i) => {
        if (v == null) {
          pen = 'M';
          return;
        }
        const x = 2 + i * step;
        const y = hi === lo ? SH / 2 : 3 + (1 - (v - lo) / span) * (SH - 6);
        spark += `${pen}${x.toFixed(1)},${y.toFixed(1)} `;
        pen = 'L';
        sparkEnd = { x, y };
      });
    }
    return { kpi: k, value: fmtValue(k.value, k.unit), delta: delta(k), status: statusLabel(k), target: targetLabel(k), spark, sparkEnd };
  }
}
