import { Component, OnInit, ViewChild, AfterViewInit } from '@angular/core';
import { Chart, registerables } from 'chart.js';
import { BaseChartDirective } from 'ng2-charts';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService, AnalyticsData } from '../../../../core/services/therapist.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

Chart.register(...registerables);

@Component({
  selector: 'app-therapist-analytics',
  standalone: false,
  templateUrl: './analytics.html',
  styleUrl: './analytics.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistAnalytics implements OnInit, AfterViewInit {
  @ViewChild('predictionChart') predictionChart?: BaseChartDirective;
  @ViewChild('confidenceChart') confidenceChart?: BaseChartDirective;

  loading = true;
  data: AnalyticsData | null = null;

  kpiCards: KpiCard[] = [];
  difficultyMatrix: DifficultyMatrixEntry[] = [];
  adaptations: Adaptation[] = [];

  predictionChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  predictionChartOptions: ChartOptions<'bar'> = {};
  confidenceChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  confidenceChartOptions: ChartOptions<'bar'> = {};

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Analíticas IA',
      subtitle: 'Rendimiento y adaptaciones del modelo',
      icon: ['fas', 'brain'],
    });
    this.loadAnalytics();
  }

  ngAfterViewInit() {
    this.initChartOptions();
  }

  private loadAnalytics() {
    this.therapistService.getAnalytics().subscribe({
      next: (res) => {
        if (res.success && res.data) {
          this.data = res.data;
          this.buildKpiCards(res.data);
          this.buildDifficultyMatrix(res.data);
          this.buildAdaptations(res.data);
          this.buildPredictionChart(res.data);
          this.buildConfidenceChart(res.data);
        }
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  private buildKpiCards(d: AnalyticsData) {
    this.kpiCards = [
      {
        icon: 'psychology',
        label: 'Adaptaciones IA',
        value: d.kpi.adaptations_count.toString(),
        suffix: '',
        color: 'text-blue-600',
        bgColor: 'bg-blue-50',
      },
      {
        icon: 'trending_up',
        label: 'Precisión Promedio',
        value: d.kpi.avg_accuracy.toFixed(1),
        suffix: '%',
        color: 'text-emerald-600',
        bgColor: 'bg-emerald-50',
      },
      {
        icon: 'check_circle',
        label: 'Tasa de Éxito',
        value: d.kpi.success_rate.toFixed(1),
        suffix: '%',
        color: 'text-primary',
        bgColor: 'bg-primary/10',
      },
      {
        icon: 'settings',
        label: 'Modelos Activos',
        value: d.kpi.active_models.toString(),
        suffix: '',
        color: 'text-purple-600',
        bgColor: 'bg-purple-50',
      },
    ];
  }

  private buildDifficultyMatrix(d: AnalyticsData) {
    this.difficultyMatrix = d.difficulty_matrix.map((entry) => ({
      game: entry.game,
      levels: entry.levels.map((l) => ({
        ...l,
        dotColor: this.getAccuracyColor(l.accuracy),
        barWidth: l.accuracy + '%',
      })),
    }));
  }

  private buildAdaptations(d: AnalyticsData) {
    this.adaptations = d.recent_adaptations || [];
  }

  private buildPredictionChart(d: AnalyticsData) {
    const labels = d.prediction_distribution.map((p) => p.label);
    const values = d.prediction_distribution.map((p) => p.value);
    const colors = ['#75a83a', '#3e6837', '#a5d087'];

    this.predictionChartData = {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: colors,
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    };
  }

  private buildConfidenceChart(d: AnalyticsData) {
    const labels = d.model_confidence.map((m) => m.model);
    const values = d.model_confidence.map((m) => m.confidence);

    this.confidenceChartData = {
      labels,
      datasets: [
        {
          data: values,
          backgroundColor: '#75a83a',
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    };
  }

  private initChartOptions() {
    const fontFamily = 'Manrope, sans-serif';

    this.predictionChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx: any) => `${ctx.parsed.y} predicciones`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            font: { family: fontFamily, size: 11 },
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        x: {
          ticks: {
            font: { family: fontFamily, size: 11, weight: '600' },
          },
          grid: { display: false },
        },
      },
    };

    this.confidenceChartOptions = {
      indexAxis: 'y' as const,
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx: any) => `${ctx.parsed.x}%`,
          },
        },
      },
      scales: {
        x: {
          beginAtZero: true,
          max: 100,
          ticks: {
            font: { family: fontFamily, size: 11 },
            callback: (v: any) => v + '%',
          },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        y: {
          ticks: {
            font: { family: fontFamily, size: 11, weight: '600' },
          },
          grid: { display: false },
        },
      },
    };
  }

  refresh() {
    this.loading = true;
    this.loadAnalytics();
  }

  exportCsv() {
    if (!this.data) return;

    const rows: string[] = ['sección,clave,valor'];
    rows.push(`kpi,Adaptaciones IA,${this.data.kpi.adaptations_count}`);
    rows.push(`kpi,Precisión Promedio,${this.data.kpi.avg_accuracy}`);
    rows.push(`kpi,Tasa de Éxito,${this.data.kpi.success_rate}`);
    rows.push(`kpi,Modelos Activos,${this.data.kpi.active_models}`);

    for (const entry of this.data.difficulty_matrix) {
      for (const level of entry.levels) {
        rows.push(`dificultad,${entry.game} / ${level.level},${level.accuracy}`);
      }
    }

    for (const p of this.data.prediction_distribution) {
      rows.push(`predicción,${p.label},${p.value}`);
    }

    for (const m of this.data.model_confidence) {
      rows.push(`confianza,${m.model},${m.confidence}`);
    }

    const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `analytics_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  private getAccuracyColor(accuracy: number): string {
    if (accuracy >= 80) return 'bg-emerald-500';
    if (accuracy >= 60) return 'bg-amber-400';
    return 'bg-red-400';
  }

  getPredictionTotal(): number {
    if (!this.data) return 0;
    return this.data.prediction_distribution.reduce((s, p) => s + p.value, 0);
  }

  getPredictionPercent(value: number): number {
    const total = this.getPredictionTotal();
    return total ? Math.round((value / total) * 100) : 0;
  }
}

interface KpiCard {
  icon: string;
  label: string;
  value: string;
  suffix: string;
  color: string;
  bgColor: string;
}

interface DifficultyMatrixEntry {
  game: string;
  levels: {
    level: string;
    accuracy: number;
    count: number;
    dotColor: string;
    barWidth: string;
  }[];
}

interface Adaptation {
  date: string;
  description: string;
  impact: 'positive' | 'neutral' | 'negative';
}

interface ChartData<T> {
  labels?: string[];
  datasets: { data: number[]; backgroundColor: string | string[]; borderRadius?: number; borderSkipped?: boolean }[];
}

interface ChartOptions<T> {
  indexAxis?: 'x' | 'y';
  responsive?: boolean;
  maintainAspectRatio?: boolean;
  plugins?: any;
  scales?: any;
}
