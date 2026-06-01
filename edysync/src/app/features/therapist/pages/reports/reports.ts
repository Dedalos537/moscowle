import { Component, OnInit, OnDestroy, ViewChild, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import {
  TherapistService,
  PatientReport,
} from '../../../../core/services/therapist.service';
import { CalendarEvent } from '../../../../core/models/appointment';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { forkJoin, Subscription } from 'rxjs';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

Chart.register(...registerables);

// chart.js type workaround for font weight
type _FontWeight = number | 'normal' | 'bold' | 'bolder' | 'lighter';

interface WeeklyData {
  week: string;
  sessions: number;
  accuracy: number;
}

@Component({
  selector: 'app-therapist-reports',
  standalone: false,
  templateUrl: './reports.html',
  styleUrl: './reports.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistReports implements OnInit, OnDestroy {
  @ViewChild('accuracyChart') accuracyChart?: any;
  @ViewChild('sessionsChart') sessionsChart?: any;

  loading = true;
  startDate = '';
  endDate = '';
  error: string | null = null;

  improvementRate = 0;
  avgSessionTime = 0;
  completedObjectives = 0;
  activePatients = 0;

  weeklyData: WeeklyData[] = [];
  allPatients: PatientReport[] = [];

  get bestPatients(): PatientReport[] {
    return [...this.allPatients]
      .sort((a, b) => b.avg_accuracy - a.avg_accuracy)
      .slice(0, 5);
  }

  get worstPatients(): PatientReport[] {
    return [...this.allPatients]
      .sort((a, b) => a.avg_accuracy - b.avg_accuracy)
      .slice(0, 5);
  }

  accuracyChartData: ChartData<'line'> = {
    labels: [],
    datasets: [
      {
        label: 'Precisión (%)',
        data: [],
        borderColor: '#75a83a',
        backgroundColor: 'rgba(117, 168, 58, 0.1)',
        fill: true,
        tension: 0.4,
        pointBackgroundColor: '#75a83a',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
        borderWidth: 2,
      },
    ],
  };
  accuracyChartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(26, 28, 22, 0.92)',
        titleFont: { family: 'Manrope', size: 12, weight: 700 as _FontWeight },
        bodyFont: { family: 'Manrope', size: 13, weight: 600 as _FontWeight },
        padding: { x: 14, y: 10 },
        cornerRadius: 10,
        displayColors: false,
        callbacks: { label: (ctx) => `${ctx.raw}%` },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { family: 'Manrope', size: 11, weight: 600 as _FontWeight }, color: '#76796c' },
      },
      y: {
        grid: { color: 'rgba(217, 219, 206, 0.3)' },
        ticks: {
          font: { family: 'Manrope', size: 11, weight: 500 as _FontWeight },
          color: '#76796c',
          callback: (val) => `${val}%`,
        },
        beginAtZero: true,
        max: 100,
      },
    },
  };
  readonly accuracyChartType = 'line' as const;

  sessionsChartData: ChartData<'bar'> = {
    labels: [],
    datasets: [
      {
        label: 'Sesiones',
        data: [],
        backgroundColor: 'rgba(117, 168, 58, 0.8)',
        borderColor: '#75a83a',
        borderWidth: 1,
        borderRadius: 8,
        barPercentage: 0.6,
      },
    ],
  };
  sessionsChartOptions: ChartConfiguration<'bar'>['options'] = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: 'rgba(26, 28, 22, 0.92)',
        titleFont: { family: 'Manrope', size: 12, weight: 700 as _FontWeight },
        bodyFont: { family: 'Manrope', size: 13, weight: 600 as _FontWeight },
        padding: { x: 14, y: 10 },
        cornerRadius: 10,
        displayColors: false,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { family: 'Manrope', size: 11, weight: 600 as _FontWeight }, color: '#76796c' },
      },
      y: {
        grid: { color: 'rgba(217, 219, 206, 0.3)' },
        ticks: { font: { family: 'Manrope', size: 11, weight: 500 as _FontWeight }, color: '#76796c' },
        beginAtZero: true,
      },
    },
  };
  readonly sessionsChartType = 'bar' as const;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Reportes',
      subtitle: 'Análisis y estadísticas de sesiones',
      icon: ['fas', 'chart-bar'],
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  private loadData() {
    this.loading = true;
    this.cdr.markForCheck();
    const now = new Date();
    const month = now.getMonth() + 1;
    const year = now.getFullYear();

    this.subs.add(forkJoin({
      overview: this.therapistService.getReportsOverview(),
      detailed: this.therapistService.getDetailedReports(),
      appointments: this.therapistService.getTherapistAppointments(month, year),
    }).subscribe({
      next: (res) => {
        if (res.overview.success && res.overview.data) {
          const o = res.overview.data;
          this.improvementRate = o.improvement_rate;
          this.avgSessionTime = o.avg_session_time_minutes;
          this.completedObjectives = o.completed_objectives;
          this.activePatients = o.active_patients;
        }

        if (res.detailed.success && res.detailed.data) {
          this.allPatients = res.detailed.data;
        }

        if (res.appointments.success && res.appointments.data) {
          this.buildWeeklyData(res.appointments.data);
        }

        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  private buildWeeklyData(events: CalendarEvent[]) {
    const weekMap = new Map<string, { sessions: number; accuracySum: number; count: number }>();

    for (const event of events) {
      const date = new Date(event.start);
      const weekStart = this.getWeekStart(date);
      const key = weekStart.toISOString().slice(0, 10);

      if (!weekMap.has(key)) {
        weekMap.set(key, { sessions: 0, accuracySum: 0, count: 0 });
      }

      const entry = weekMap.get(key)!;
      entry.sessions++;
    }

    const sorted = Array.from(weekMap.entries()).sort(([a], [b]) => a.localeCompare(b));

    this.weeklyData = sorted.map(([key, val]) => {
      const d = new Date(key);
      const monthName = d.toLocaleDateString('es-ES', { month: 'short' });
      const day = d.getDate();
      const weekLabel = `${monthName} ${day}`;
      return {
        week: weekLabel,
        sessions: val.sessions,
        accuracy: val.count > 0 ? Math.round((val.accuracySum / val.count) * 10) / 10 : 0,
      };
    });

    this.updateCharts();
  }

  private getWeekStart(date: Date): Date {
    const d = new Date(date);
    const day = d.getDay();
    const diff = d.getDate() - day + (day === 0 ? -6 : 1);
    d.setDate(diff);
    d.setHours(0, 0, 0, 0);
    return d;
  }

  private updateCharts() {
    const labels = this.weeklyData.map((w) => w.week);
    const accuracies = this.weeklyData.map((w) => w.accuracy);
    const sessions = this.weeklyData.map((w) => w.sessions);

    this.accuracyChartData = {
      ...this.accuracyChartData,
      labels,
      datasets: [
        {
          ...this.accuracyChartData.datasets[0],
          data: accuracies,
        },
      ],
    };

    this.sessionsChartData = {
      ...this.sessionsChartData,
      labels,
      datasets: [
        {
          ...this.sessionsChartData.datasets[0],
          data: sessions,
        },
      ],
    };
  }

  onFilterChange() {
    this.loading = true;
    this.cdr.markForCheck();
    const now = new Date();
    const month = now.getMonth() + 1;
    const year = now.getFullYear();

    this.subs.add(forkJoin({
      overview: this.therapistService.getReportsOverview(),
      detailed: this.therapistService.getDetailedReports(this.startDate || undefined, this.endDate || undefined),
      appointments: this.therapistService.getTherapistAppointments(month, year),
    }).subscribe({
      next: (res) => {
        if (res.overview.success && res.overview.data) {
          const o = res.overview.data;
          this.improvementRate = o.improvement_rate;
          this.avgSessionTime = o.avg_session_time_minutes;
          this.completedObjectives = o.completed_objectives;
          this.activePatients = o.active_patients;
        }
        if (res.detailed.success && res.detailed.data) {
          this.allPatients = res.detailed.data;
        }
        if (res.appointments.success && res.appointments.data) {
          this.buildWeeklyData(res.appointments.data);
        }
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  exportCSV() {
    const now = new Date().toISOString().slice(0, 10);
    const rows = [['Paciente', 'Sesiones', 'Precisión', 'Progreso']];
    for (const p of this.allPatients) {
      rows.push([p.patient_name, String(p.sessions_count), `${p.avg_accuracy}%`, `${p.avg_accuracy}%`]);
    }
    const csv = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `reporte_pacientes_${now}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

}
