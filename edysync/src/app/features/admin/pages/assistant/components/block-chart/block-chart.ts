import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration } from 'chart.js';
import { GlobalSettingsService } from '../../../../../../core/services/global-settings.service';
import { AssistantBlock, ValueFormat } from '../../../../../../core/services/assistant';
import { formatValue } from '../message-blocks/format';

Chart.register(...registerables);

type ChartBlock = Extract<AssistantBlock, { type: 'chart' }>;

/** Colores por serie en orden fijo (no por posición en el ranking): verde de la marca, azul, ámbar, violeta, terracota, verde azulado. */
const SERIES = ['#5e8f2f', '#2f6db3', '#c27a12', '#8a4fb8', '#c2410c', '#0f8b8d'];

/** Gráfica de una respuesta del asistente. Con «Ocultar gráficos» activo (o a pedido) se ve como tabla. */
@Component({
  selector: 'app-block-chart',
  standalone: true,
  imports: [BaseChartDirective],
  templateUrl: './block-chart.html',
  styleUrl: './block-chart.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BlockChart {
  readonly block = input.required<ChartBlock>();
  private settings = inject(GlobalSettingsService);
  readonly asTable = signal(this.settings.hideCharts());

  readonly config = computed<ChartConfiguration>(() => {
    const b = this.block();
    const css = getComputedStyle(document.documentElement);
    const ink = css.getPropertyValue('--color-on-surface-variant').trim() || '#43493a';
    const grid = css.getPropertyValue('--color-outline-variant').trim() || '#c3c9b5';
    const surface = css.getPropertyValue('--color-surface-container-lowest').trim() || '#fff';
    const fmt = (v: number | null) => formatValue(v, b.format);
    const doughnut = b.kind === 'doughnut';
    return {
      type: b.kind,
      data: {
        labels: b.x,
        datasets: b.series.map((s, i) => ({
          label: s.name,
          data: s.data as number[],
          backgroundColor: doughnut ? b.x.map((_, j) => SERIES[j % SERIES.length]) : SERIES[i % SERIES.length],
          borderColor: doughnut ? surface : SERIES[i % SERIES.length],
          borderWidth: doughnut ? 2 : 2,
          borderRadius: b.kind === 'bar' ? 4 : 0,
          pointRadius: b.kind === 'line' ? 3 : 0,
          pointHoverRadius: 5,
          tension: 0.3,
          spanGaps: true,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: doughnut ? 'nearest' : 'index', intersect: false },
        plugins: {
          legend: { display: b.series.length > 1 || doughnut, position: 'bottom', labels: { color: ink, boxWidth: 12, usePointStyle: true } },
          tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label ?? ''}: ${fmt(ctx.parsed as unknown as number)}`.replace(/^: /, '') } },
        },
        scales: doughnut
          ? {}
          : {
              x: { ticks: { color: ink, maxRotation: 0, autoSkip: true }, grid: { display: false } },
              y: { beginAtZero: true, ticks: { color: ink, callback: (v) => fmt(Number(v)) }, grid: { color: grid } },
            },
      },
    } as ChartConfiguration;
  });

  value(v: number | null, format: ValueFormat): string {
    return formatValue(v, format);
  }
}
