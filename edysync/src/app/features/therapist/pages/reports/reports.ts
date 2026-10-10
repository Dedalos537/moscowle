import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, computed, inject, signal, TemplateRef, ViewChild } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AiRecommendation, InsightsPatient, TherapistInsights, TherapistService } from '../../../../core/services/therapist.service';
import { toLocalDateString } from '../../../../core/utils/date.util';
import { Button } from '../../../../shared/components/button/button';

type Tab = 'summary' | 'patients' | 'ai';
type Period = '4w' | '12w' | 'year';
type SortKey = 'attention' | 'name' | 'accuracy' | 'trend' | 'attendance' | 'sessions';

const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
// Gráficas: coordenadas del viewBox.
const W = 520;
const H = 180;
const PAD = { l: 8, r: 8, t: 22, b: 24 };

function dayLabel(iso: string) {
  const [, m, d] = iso.split('-').map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}

/**
 * Reportes del terapeuta: sesiones, asistencia y progreso en juegos, más las recomendaciones del modelo de la IA
 * (antes «Analíticas IA» era una pestaña aparte con cifras fijas en el código). Todo viene de /therapist/api/insights.
 */
@Component({
  selector: 'app-therapist-reports',
  standalone: true,
  imports: [FontAwesomeModule, Button],
  templateUrl: './reports.html',
  styleUrl: './reports.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TherapistReports implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;

  private headerService = inject(HeaderService);
  private therapistService = inject(TherapistService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private sub?: Subscription;

  readonly W = W;
  readonly H = H;
  readonly PAD = PAD;
  readonly tabs: { key: Tab; label: string }[] = [
    { key: 'summary', label: 'Resumen' },
    { key: 'patients', label: 'Pacientes' },
    { key: 'ai', label: 'IA y juegos' },
  ];
  readonly periods: { key: Period; label: string }[] = [
    { key: '4w', label: '4 semanas' },
    { key: '12w', label: '12 semanas' },
    { key: 'year', label: 'Este año' },
  ];

  readonly tab = signal<Tab>('summary');
  readonly period = signal<Period>('4w');
  readonly data = signal<TherapistInsights | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly onlyAttention = signal(false);
  readonly sort = signal<{ key: SortKey; dir: 1 | -1 }>({ key: 'attention', dir: 1 });
  readonly hoverWeek = signal<number | null>(null);

  readonly rangeLabel = computed(() => {
    const r = this.data()?.range;
    return r ? `${dayLabel(r.from)} – ${dayLabel(r.to)}` : '';
  });

  readonly attentionCount = computed(() => (this.data()?.patients ?? []).filter((p) => p.attention.length).length);

  readonly patients = computed(() => {
    const list = (this.data()?.patients ?? []).filter((p) => !this.onlyAttention() || p.attention.length);
    const { key, dir } = this.sort();
    const val = (p: InsightsPatient): number | string => {
      switch (key) {
        case 'name':
          return p.name.toLowerCase();
        case 'accuracy':
          return p.accuracy ?? -1;
        case 'trend':
          return p.trend ?? -999;
        case 'attendance':
          return p.attendance ?? -1;
        case 'sessions':
          return p.sessions_done;
        default:
          return -p.attention.length;
      }
    };
    return [...list].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      const c = va < vb ? -1 : va > vb ? 1 : a.name.localeCompare(b.name);
      return c * (key === 'name' || key === 'attention' ? dir : -dir);
    });
  });

  /** Barras de sesiones realizadas por semana (sobre las programadas, en contorno). */
  readonly sessionsChart = computed(() => {
    const weeks = this.data()?.weekly ?? [];
    if (!weeks.length) return null;
    const max = Math.max(1, ...weeks.map((w) => w.sessions_scheduled));
    const slot = (W - PAD.l - PAD.r) / weeks.length;
    const bw = Math.min(28, slot * 0.6);
    const y = (v: number) => PAD.t + (1 - v / max) * (H - PAD.t - PAD.b);
    const bar = (x: number, v: number) => {
      const h = Math.max(v ? 2 : 0, H - PAD.b - y(v));
      const top = H - PAD.b - h;
      const r = Math.min(4, h, bw / 2);
      return h ? `M${x},${H - PAD.b} V${top + r} Q${x},${top} ${x + r},${top} H${x + bw - r} Q${x + bw},${top} ${x + bw},${top + r} V${H - PAD.b} Z` : '';
    };
    const showEvery = Math.ceil(weeks.length / 8);
    return {
      max,
      bars: weeks.map((w, i) => {
        const x = PAD.l + slot * i + (slot - bw) / 2;
        return {
          i,
          cx: x + bw / 2,
          hitX: PAD.l + slot * i,
          hitW: slot,
          planned: bar(x, w.sessions_scheduled),
          done: bar(x, w.sessions_done),
          topY: y(w.sessions_scheduled),
          label: i % showEvery === 0 ? dayLabel(w.week) : '',
          week: w,
        };
      }),
    };
  });

  /** Línea de precisión semanal (huecos donde no hubo partidas). */
  readonly accuracyChart = computed(() => {
    const weeks = this.data()?.weekly ?? [];
    if (weeks.filter((w) => w.accuracy != null).length < 1) return null;
    const slot = (W - PAD.l - PAD.r) / weeks.length;
    const y = (v: number) => PAD.t + (1 - v / 100) * (H - PAD.t - PAD.b);
    let d = '';
    let pen = 'M';
    const points: { x: number; y: number; v: number; i: number }[] = [];
    weeks.forEach((w, i) => {
      if (w.accuracy == null) {
        pen = 'M';
        return;
      }
      const x = PAD.l + slot * i + slot / 2;
      d += `${pen}${x.toFixed(1)},${y(w.accuracy).toFixed(1)} `;
      pen = 'L';
      points.push({ x, y: y(w.accuracy), v: w.accuracy, i });
    });
    const showEvery = Math.ceil(weeks.length / 8);
    return {
      d,
      points,
      grid: [0, 50, 100].map((v) => ({ y: y(v), label: `${v}%` })),
      ticks: weeks.map((w, i) => ({ x: PAD.l + slot * i + slot / 2, label: i % showEvery === 0 ? dayLabel(w.week) : '' })),
      last: points[points.length - 1],
    };
  });

  readonly hovered = computed(() => {
    const i = this.hoverWeek();
    const w = i == null ? null : this.data()?.weekly[i];
    return w ? { i, ...w, label: `Semana del ${dayLabel(w.week)}` } : null;
  });

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Reportes',
      subtitle: 'Sesiones, progreso y recomendaciones de la IA',
      icon: ['fas', 'chart-line'],
      actionTemplate: this.headerActions,
    });
    const qp = this.route.snapshot.queryParamMap;
    const t = qp.get('tab') as Tab | null;
    if (t && this.tabs.some((x) => x.key === t)) this.tab.set(t);
    const p = qp.get('period') as Period | null;
    if (p && this.periods.some((x) => x.key === p)) this.period.set(p);
    this.load();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.sub?.unsubscribe();
  }

  load() {
    // Semanas completas (lunes a domingo) para que la primera barra no quede casi vacía.
    const today = new Date();
    const from = new Date(today);
    if (this.period() === 'year') from.setMonth(0, 1);
    else {
      from.setDate(today.getDate() - ((today.getDay() + 6) % 7) - 7 * (this.period() === '12w' ? 11 : 3));
    }
    this.loading.set(true);
    this.error.set(null);
    this.sub?.unsubscribe();
    this.sub = this.therapistService.getInsights(toLocalDateString(from), toLocalDateString(today)).subscribe({
      next: (r) => {
        this.data.set(r.data ?? null);
        this.loading.set(false);
      },
      error: (e) => {
        this.loading.set(false);
        this.error.set(e?.error?.error || 'No se pudieron cargar los reportes.');
      },
    });
  }

  setTab(t: Tab) {
    this.tab.set(t);
    this.router.navigate([], { queryParams: { tab: t === 'summary' ? null : t }, queryParamsHandling: 'merge', replaceUrl: true });
  }

  onTabKey(ev: KeyboardEvent) {
    const i = this.tabs.findIndex((t) => t.key === this.tab());
    const next = ev.key === 'ArrowRight' ? i + 1 : ev.key === 'ArrowLeft' ? i - 1 : null;
    if (next == null) return;
    ev.preventDefault();
    const t = this.tabs[(next + this.tabs.length) % this.tabs.length];
    this.setTab(t.key);
    queueMicrotask(() => document.getElementById(`rp-tab-${t.key}`)?.focus());
  }

  setPeriod(p: Period) {
    if (p === this.period()) return;
    this.period.set(p);
    this.router.navigate([], { queryParams: { period: p === '4w' ? null : p }, queryParamsHandling: 'merge', replaceUrl: true });
    this.load();
  }

  sortBy(key: SortKey) {
    const s = this.sort();
    this.sort.set({ key, dir: s.key === key ? (s.dir === 1 ? -1 : 1) : 1 });
  }

  ariaSort(key: SortKey) {
    const s = this.sort();
    if (s.key !== key) return 'none';
    const asc = (key === 'name' || key === 'attention' ? s.dir : -s.dir) === 1;
    return asc ? 'ascending' : 'descending';
  }

  openPatient(id: number) {
    this.router.navigate(['/therapist/patients', id]);
  }

  pct(v: number | null | undefined) {
    return v == null ? '—' : `${String(v).replace('.', ',')} %`;
  }

  trendText(t: number | null) {
    if (t == null) return '—';
    if (Math.abs(t) < 1) return '= estable';
    return `${t > 0 ? '↑' : '↓'} ${String(Math.abs(t)).replace('.', ',')} pts`;
  }

  recLabel(r: AiRecommendation | null) {
    return r ? (this.data()?.ai.labels[r] ?? r) : '—';
  }

  date(iso: string | null) {
    return iso ? dayLabel(iso) : '—';
  }

  exportCsv() {
    const d = this.data();
    if (!d) return;
    const esc = (v: unknown) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const rows = [
      ['Paciente', 'Sesiones realizadas', 'Sesiones programadas', 'Asistencia %', 'Partidas', 'Precisión %', 'Tendencia (pts)', 'Recomendación IA', 'Última sesión', 'Requiere atención'],
      ...d.patients.map((p) => [
        p.name,
        p.sessions_done,
        p.sessions_scheduled,
        p.attendance ?? '',
        p.games,
        p.accuracy ?? '',
        p.trend ?? '',
        p.recommendation ? d.ai.labels[p.recommendation] : '',
        p.last_session ?? '',
        p.attention.join('; '),
      ]),
    ];
    const csv = rows.map((r) => r.map(esc).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporte_${d.range.from}_${d.range.to}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
}
