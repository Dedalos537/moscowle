import { Component, OnInit, OnDestroy, ViewChild, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { BaseChartDirective } from 'ng2-charts';
import { Chart, registerables } from 'chart.js';
import type { ChartConfiguration, ChartData } from 'chart.js';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { LogViewerService, LogEntry } from '../../../../core/services/log-viewer.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { CSPReport, CSPReportFilter } from '../../../../core/models/csp-report';
import { AdminAPIToken } from '../../../../core/models/api-token';
import { Subscription, firstValueFrom, interval } from 'rxjs';
import { fadeInUp, scaleIn, listStagger, cardEnter } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Input } from '../../../../shared/components/input/input';
import { Alert } from '../../../../shared/components/alert/alert';
import { Modal } from '../../../../shared/components/modal/modal';
import { Incidents } from '../incidents/incidents';

Chart.register(...registerables);

type TabId = 'railway' | 'logs' | 'csp' | 'tokens' | 'incidents';

// Prometheus-inspired color palette
const COLORS = {
  blue:   { line: 'rgb(59, 130, 246)',  fill: 'rgba(59,130,246,0.15)' },
  green:  { line: 'rgb(16, 185, 129)',  fill: 'rgba(16,185,129,0.15)' },
  purple: { line: 'rgb(139, 92, 246)',  fill: 'rgba(139,92,246,0.15)' },
  orange: { line: 'rgb(251, 146, 60)',  fill: 'rgba(251,146,60,0.15)' },
  red:    { line: 'rgb(239, 68, 68)',   fill: 'rgba(239,68,68,0.15)' },
  cyan:   { line: 'rgb(34, 211, 238)',  fill: 'rgba(34,211,238,0.15)' },
  yellow: { line: 'rgb(234, 179, 8)',   fill: 'rgba(234,179,8,0.15)' },
  pink:   { line: 'rgb(236, 72, 153)',  fill: 'rgba(236,72,153,0.15)' },
};

@Component({
  selector: 'app-visor-funcionamiento',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, BaseChartDirective, Button, Spinner, Input, Alert, Modal, Incidents],
  templateUrl: './visor-funcionamiento.html',
  styleUrl: './visor-funcionamiento.scss',
  animations: [fadeInUp, scaleIn, listStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VisorFuncionamiento implements OnInit, OnDestroy {
  activeTab: TabId = 'railway';

  private headerService = inject(HeaderService);
  private admin = inject(AdminService);
  private logViewer = inject(LogViewerService);
  private confirmService = inject(ConfirmService);
  private cdr = inject(ChangeDetectorRef);

  private subs = new Subscription();

  @ViewChild('cpuChart') cpuChartRef?: BaseChartDirective;
  @ViewChild('memChart') memChartRef?: BaseChartDirective;
  @ViewChild('diskChart') diskChartRef?: BaseChartDirective;
  @ViewChild('netChart') netChartRef?: BaseChartDirective;
  @ViewChild('reqChart') reqChartRef?: BaseChartDirective;
  @ViewChild('errChart') errChartRef?: BaseChartDirective;
  @ViewChild('latChart') latChartRef?: BaseChartDirective;

  // --- Railway history ---
  railwayLoading = true;
  railwayError: string | null = null;
  railwayDateFrom = '';
  railwayDateTo = '';
  railwaySnapshot: any = null;
  appMetrics: any = null;

  cpuChartData: ChartData<'line'> = { labels: [], datasets: [] };
  cpuChartOptions: ChartConfiguration<'line'>['options'] = {};
  memChartData: ChartData<'line'> = { labels: [], datasets: [] };
  memChartOptions: ChartConfiguration<'line'>['options'] = {};
  diskChartData: ChartData<'line'> = { labels: [], datasets: [] };
  diskChartOptions: ChartConfiguration<'line'>['options'] = {};
  netChartData: ChartData<'line'> = { labels: [], datasets: [] };
  netChartOptions: ChartConfiguration<'line'>['options'] = {};
  reqChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  reqChartOptions: ChartConfiguration<'bar'>['options'] = {};
  errChartData: ChartData<'line'> = { labels: [], datasets: [] };
  errChartOptions: ChartConfiguration<'line'>['options'] = {};
  latChartData: ChartData<'bar'> = { labels: [], datasets: [] };
  latChartOptions: ChartConfiguration<'bar'>['options'] = {};

  // --- Logs ---
  logs: LogEntry[] = [];
  logsLoading = true;
  logsError: string | null = null;
  logsLevelFilter = '';
  logsSearchQuery = '';
  logsExpandedIndex: number | null = null;
  logsAutoRefresh = false;
  private logsRefreshSub?: Subscription;
  readonly logsLevels = ['', 'ERROR', 'WARNING', 'INFO', 'DEBUG'];

  // --- CSP ---
  cspReports: CSPReport[] = [];
  cspLoading = false;
  cspError: string | null = null;
  cspTotal = 0;
  cspPage = 1;
  cspPages = 1;
  cspFilter: CSPReportFilter = { directive: '', blocked_uri: '', since: '' };

  // --- Tokens ---
  tokens: AdminAPIToken[] = [];
  tokensLoading = false;
  tokensError: string | null = null;
  showCreateModal = false;
  rotate = false;
  newToken: string | null = null;
  creating = false;

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Centro de Operaciones',
      subtitle: 'Métricas, logs y seguridad del sistema',
      icon: ['fas', 'desktop'],
    });
    const now = new Date();
    // Default range: last 7 days in Lima time
    const limaOffset = -5 * 60;
    const nowLima = new Date(now.getTime() + (limaOffset - now.getTimezoneOffset()) * 60000);
    const weekAgoLima = new Date(nowLima.getTime() - 7 * 24 * 60 * 60 * 1000);
    this.railwayDateFrom = this.toLocalISO(weekAgoLima);
    this.railwayDateTo = this.toLocalISO(nowLima);
    this.loadRailwayHistory();
    this.loadRailwaySnapshot();
    this.loadAppMetrics();
    this.loadLogs();
    this.loadCspReports();
    this.loadTokens();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
    this.logsRefreshSub?.unsubscribe();
  }

  switchTab(tab: TabId) {
    this.activeTab = tab;
    if (tab === 'railway') {
      setTimeout(() => {
        [this.cpuChartRef, this.memChartRef, this.diskChartRef, this.netChartRef,
         this.reqChartRef, this.errChartRef, this.latChartRef].forEach(c => c?.update());
      }, 100);
    }
  }

  // --- Railway ---
  loadRailwaySnapshot() {
    this.subs.add(
      this.admin.getRailwayMetrics().subscribe({
        next: (res) => { this.railwaySnapshot = res; this.cdr.markForCheck(); },
        error: () => {},
      })
    );
  }

  loadAppMetrics() {
    this.subs.add(
      this.admin.getAppMetrics().subscribe({
        next: (res) => {
          this.appMetrics = res;
          if (res?.data) {
            this.buildAppCharts(res.data);
          }
          this.cdr.markForCheck();
        },
        error: () => {},
      })
    );
  }

  private buildAppCharts(data: any) {
    const tooltipBase = {
      backgroundColor: 'rgba(15,23,42,0.95)',
      titleColor: '#e2e8f0',
      bodyColor: '#cbd5e1',
      borderColor: 'rgba(100,116,139,0.3)',
      borderWidth: 1,
      padding: 10,
      cornerRadius: 6,
    };

    // Requests by status
    const bs = data.requests.by_status;
    this.reqChartData = {
      labels: ['2xx', '3xx', '4xx', '5xx'],
      datasets: [{
        data: [bs['2xx'] || 0, bs['3xx'] || 0, bs['4xx'] || 0, bs['5xx'] || 0],
        backgroundColor: ['#22c55e', '#3b82f6', '#f59e0b', '#ef4444'],
        borderRadius: 4,
        borderSkipped: false,
      }],
    };
    this.reqChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: tooltipBase,
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 11, weight: 'bold' } } },
        y: { beginAtZero: true, grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: '#64748b', font: { size: 10 } } },
      },
    };

    // Response time percentiles
    const lat = data.latency;
    this.latChartData = {
      labels: ['avg', 'p50', 'p95', 'p99', 'max'],
      datasets: [{
        data: [lat.avg_ms, lat.p50_ms, lat.p95_ms, lat.p99_ms, lat.max_ms],
        backgroundColor: ['#22d3ee', '#3b82f6', '#eab308', '#f97316', '#ef4444'],
        borderRadius: 4,
        borderSkipped: false,
      }],
    };
    this.latChartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          ...tooltipBase,
          callbacks: { label: (ctx: any) => `${ctx.parsed?.y ?? 0} ms` },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: '#64748b', font: { size: 11, weight: 'bold' } } },
        y: { beginAtZero: true, grid: { color: 'rgba(148,163,184,0.08)' }, ticks: { color: '#64748b', font: { size: 10 }, callback: (v: any) => `${v}ms` } },
      },
    };
  }

  loadRailwayHistory() {
    this.railwayLoading = true;
    this.railwayError = null;
    this.subs.add(
      this.admin.getRailwayMetricsHistory(
        this.railwayDateFrom ? new Date(this.railwayDateFrom).toISOString() : undefined,
        this.railwayDateTo ? new Date(this.railwayDateTo).toISOString() : undefined,
      ).subscribe({
        next: (res) => {
          this.railwayLoading = false;
          if (!res.success || !res.data) {
            this.railwayError = res.error || 'Error al cargar histórico';
            this.cdr.markForCheck();
            return;
          }
          this.buildAllCharts(res.data);
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.railwayLoading = false;
          this.railwayError = err.error?.message || err.message || 'Error al cargar histórico';
          this.cdr.markForCheck();
        },
      })
    );
  }

  // --- Prometheus-style chart helpers ---

  private toLocalISO(d: Date): string {
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }

  /** Aggregate raw {ts,value} points by Lima-day → {day, avg}[] */
  private aggregateByDay(values: { ts: string; value: number }[]): { day: string; avg: number }[] {
    const buckets = new Map<string, { sum: number; count: number }>();
    for (const v of values) {
      // Parse ts → Lima date key (YYYY-MM-DD)
      const d = new Date(v.ts);
      const limaStr = d.toLocaleDateString('sv-SE', { timeZone: 'America/Lima' }); // 'YYYY-MM-DD'
      const b = buckets.get(limaStr) || { sum: 0, count: 0 };
      b.sum += v.value;
      b.count += 1;
      buckets.set(limaStr, b);
    }
    return Array.from(buckets.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([day, { sum, count }]) => ({ day, avg: +(sum / count).toFixed(4) }));
  }

  /** Format day keys to short labels like "22 jul" */
  private dayLabels(days: string[]): string[] {
    return days.map(d => {
      const [y, m, dd] = d.split('-').map(Number);
      const dt = new Date(y, m - 1, dd);
      return dt.toLocaleString('es-PE', { month: 'short', day: 'numeric', timeZone: 'America/Lima' });
    });
  }

  private promLineOptions(unit: string, data?: number[]): ChartConfiguration<'line'>['options'] {
    const maxVal = data?.length ? Math.max(...data.filter(v => v > 0), 1) : 1;
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: 'rgba(15,23,42,0.95)',
          titleColor: '#e2e8f0',
          bodyColor: '#cbd5e1',
          borderColor: 'rgba(100,116,139,0.3)',
          borderWidth: 1,
          padding: 10,
          cornerRadius: 6,
          titleFont: { weight: 'bold', size: 11 },
          bodyFont: { size: 11 },
          callbacks: { label: (ctx) => `${(ctx.parsed.y ?? 0).toFixed(3)} ${unit}` },
        },
      },
      scales: {
        x: {
          grid: { color: 'rgba(148,163,184,0.08)' },
          border: { display: false },
          ticks: { color: '#64748b', maxRotation: 45, font: { size: 9 } },
        },
        y: {
          beginAtZero: true,
          suggestedMax: Math.ceil(maxVal * 1.3),
          grid: { color: 'rgba(148,163,184,0.08)' },
          border: { display: false },
          ticks: { color: '#64748b', font: { size: 10 }, callback: (v) => `${v} ${unit}` },
        },
      },
    };
  }

  private buildAllCharts(data: any) {
    const s = data.series;
    if (!s?.CPU_USAGE?.length) { this.railwayError = 'No hay datos de Railway para el rango seleccionado'; return; }

    // Aggregate all metrics by day
    const cpuAgg = this.aggregateByDay(s.CPU_USAGE);
    const memAgg = s.MEMORY_USAGE_GB?.length ? this.aggregateByDay(s.MEMORY_USAGE_GB) : [];
    const diskAgg = s.DISK_USAGE_GB?.length ? this.aggregateByDay(s.DISK_USAGE_GB) : [];
    const rxAgg = s.NETWORK_RX_GB?.length ? this.aggregateByDay(s.NETWORK_RX_GB) : [];
    const txAgg = s.NETWORK_TX_GB?.length ? this.aggregateByDay(s.NETWORK_TX_GB) : [];

    // Use the longest series for labels
    const allDays = [cpuAgg, memAgg, diskAgg, rxAgg, txAgg]
      .reduce<string[]>((acc, a) => acc.length >= a.length ? acc : a.map(d => d.day), []);
    const ts = this.dayLabels(allDays);

    if (!ts.length) { this.railwayError = 'No hay datos de Railway para el rango seleccionado'; return; }

    // Helper: align aggregated values to the full day list
    const align = (agg: { day: string; avg: number }[]): number[] =>
      allDays.map(d => agg.find(a => a.day === d)?.avg ?? 0);

    // CPU
    const cpuVals = align(cpuAgg);
    this.cpuChartData = {
      labels: ts,
      datasets: [{
        label: 'CPU', data: cpuVals,
        borderColor: COLORS.blue.line, backgroundColor: COLORS.blue.fill,
        borderWidth: 1.5, fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5,
      }],
    };
    this.cpuChartOptions = this.promLineOptions('vCPU', cpuVals);

    // Memory
    if (memAgg.length) {
      const memVals = align(memAgg);
      this.memChartData = {
        labels: ts,
        datasets: [{
          label: 'Memory', data: memVals,
          borderColor: COLORS.green.line, backgroundColor: COLORS.green.fill,
          borderWidth: 1.5, fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5,
        }],
      };
      this.memChartOptions = this.promLineOptions('GB', memVals);
    }

    // Disk
    if (diskAgg.length) {
      const diskVals = align(diskAgg);
      this.diskChartData = {
        labels: ts,
        datasets: [{
          label: 'Disk', data: diskVals,
          borderColor: COLORS.purple.line, backgroundColor: COLORS.purple.fill,
          borderWidth: 1.5, fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5,
        }],
      };
      this.diskChartOptions = this.promLineOptions('GB', diskVals);
    }

    // Network (dual axis: RX + TX)
    if (rxAgg.length) {
      const rx = align(rxAgg);
      const tx = txAgg.length ? align(txAgg) : [];
      const allNet = [...rx, ...tx].filter((v: number) => v > 0);
      this.netChartData = {
        labels: ts,
        datasets: [
          { label: 'Ingress (RX)', data: rx, borderColor: COLORS.cyan.line, backgroundColor: COLORS.cyan.fill, borderWidth: 1.5, fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 },
          ...(tx.length ? [{ label: 'Egress (TX)', data: tx, borderColor: COLORS.orange.line, backgroundColor: COLORS.orange.fill, borderWidth: 1.5, fill: true, tension: 0.3, pointRadius: 2, pointHoverRadius: 5 }] : []),
        ],
      };
      const baseOpts = this.promLineOptions('GB', allNet);
      this.netChartOptions = {
        ...baseOpts,
        plugins: {
          legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: { size: 10 }, color: '#94a3b8' } },
          tooltip: (baseOpts as any)?.plugins?.tooltip,
        },
      } as any;
    }
  }

  // --- Logs ---
  loadLogs() {
    this.logsLoading = true;
    this.logsError = null;
    this.subs.add(
      this.logViewer.getLogs(this.logsLevelFilter || undefined, 200, this.logsSearchQuery || undefined).subscribe({
        next: (res) => { this.logs = res.logs; this.logsLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.logsLoading = false; this.logsError = err.error?.message || err.message || 'Error al cargar logs'; this.cdr.markForCheck(); },
      })
    );
  }

  setLogsLevel(level: string) {
    this.logsLevelFilter = level;
    this.loadLogs();
  }

  searchLogs() {
    this.loadLogs();
  }

  toggleLogExpand(index: number) {
    this.logsExpandedIndex = this.logsExpandedIndex === index ? null : index;
  }

  toggleLogsAutoRefresh() {
    this.logsAutoRefresh = !this.logsAutoRefresh;
    if (this.logsAutoRefresh) {
      this.logsRefreshSub = interval(5000).subscribe(() => this.loadLogs());
    } else {
      this.logsRefreshSub?.unsubscribe();
    }
  }

  logLevelColor(level: string): string {
    const map: Record<string, string> = {
      ERROR: 'var(--color-error)',
      WARNING: 'var(--color-warning)',
      INFO: 'var(--color-info)',
      DEBUG: 'var(--color-outline)',
      CRITICAL: 'var(--color-error)',
    };
    return map[level] || 'var(--color-on-surface-variant)';
  }

  // --- CSP ---
  loadCspReports() {
    this.cspLoading = true;
    this.cspError = null;
    this.subs.add(
      this.admin.getCSPReports({ ...this.cspFilter, page: this.cspPage, per_page: 25 }).subscribe({
        next: (res) => { this.cspReports = res.items; this.cspTotal = res.total; this.cspPage = res.page; this.cspPages = res.pages; this.cspLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.cspLoading = false; this.cspError = err.error?.message || err.message || 'Error al cargar CSP'; this.cdr.markForCheck(); },
      })
    );
  }

  onCspFilterChange() { this.cspPage = 1; this.loadCspReports(); }

  goToCspPage(p: number) { this.cspPage = p; this.loadCspReports(); }

  exportCspCsv() {
    this.subs.add(
      this.admin.exportCSPReportsCsv(this.cspFilter).subscribe({
        next: blob => { const url = window.URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = 'csp-reports.csv'; a.click(); window.URL.revokeObjectURL(url); this.cdr.markForCheck(); },
        error: (err) => { this.cspError = err.error?.message || err.message || 'Error al exportar'; this.cdr.markForCheck(); },
      })
    );
  }

  // --- Tokens ---
  loadTokens() {
    this.tokensLoading = true;
    this.tokensError = null;
    this.subs.add(
      this.admin.getAPITokens().subscribe({
        next: (res) => { this.tokens = res.tokens; this.tokensLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.tokensLoading = false; this.tokensError = err.error?.message || err.message || 'Error al cargar tokens'; this.cdr.markForCheck(); },
      })
    );
  }

  openCreateTokenModal() { this.showCreateModal = true; this.rotate = false; this.newToken = null; }

  closeCreateTokenModal() { this.showCreateModal = false; }

  createToken() {
    this.creating = true;
    this.subs.add(
      this.admin.createAPIToken(this.rotate).subscribe({
        next: (res) => { this.newToken = res.token; this.creating = false; this.loadTokens(); this.cdr.markForCheck(); },
        error: (err) => { this.creating = false; this.tokensError = err.error?.message || err.message || 'Error al crear token'; this.cdr.markForCheck(); },
      })
    );
  }

  async deactivateToken(id: number) {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Desactivar Token',
      message: '¿Estás seguro de que deseas desactivar este token?',
      confirmText: 'Desactivar',
      cancelText: 'Cancelar',
      variant: 'danger',
    }));
    if (!confirmed) return;
    this.subs.add(
      this.admin.deactivateAPIToken(id).subscribe({
        next: () => { this.loadTokens(); this.cdr.markForCheck(); },
        error: (err) => { this.tokensError = err.error?.message || err.message || 'Error al desactivar'; this.cdr.markForCheck(); },
      })
    );
  }

  copyToken(token: string) {
    navigator.clipboard.writeText(token);
  }
}
