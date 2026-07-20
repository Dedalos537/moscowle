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
  @ViewChild('netChart') netChartRef?: BaseChartDirective;

  // --- Railway history ---
  railwayLoading = true;
  railwayError: string | null = null;
  railwayDateFrom = '';
  railwayDateTo = '';
  railwaySnapshot: any = null;

  cpuChartData: ChartData<'line'> = { labels: [], datasets: [] };
  cpuChartOptions: ChartConfiguration<'line'>['options'] = {};
  memChartData: ChartData<'line'> = { labels: [], datasets: [] };
  memChartOptions: ChartConfiguration<'line'>['options'] = {};
  netChartData: ChartData<'line'> = { labels: [], datasets: [] };
  netChartOptions: ChartConfiguration<'line'>['options'] = {};

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
    const yesterday = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    this.railwayDateFrom = yesterday.toISOString().slice(0, 16);
    this.railwayDateTo = now.toISOString().slice(0, 16);
    this.loadRailwayHistory();
    this.loadRailwaySnapshot();
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
      setTimeout(() => { [this.cpuChartRef, this.memChartRef, this.netChartRef].forEach(c => c?.update()); }, 100);
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

  private timestamps(values: any[]): string[] {
    return values.map((v: any) => {
      const d = new Date(v.ts);
      return d.toLocaleString('es-PE', { hour: '2-digit', minute: '2-digit', second: '2-digit', month: 'short', day: 'numeric' });
    });
  }

  private lineOptions(data: number[], unit: string, suggestedMaxOverride?: number): ChartConfiguration<'line'>['options'] {
    const filtered = data.filter(v => v > 0);
    const maxVal = filtered.length ? Math.max(...filtered) : 1;
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: (ctx) => `${ctx.parsed.y} ${unit}` },
        },
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 9 } } },
        y: {
          beginAtZero: true,
          suggestedMax: suggestedMaxOverride ?? Math.ceil(maxVal * 1.3),
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: { font: { size: 10 }, callback: (v) => `${v}${unit ? ' ' + unit : ''}` },
        },
      },
    };
  }

  private buildAllCharts(data: any) {
    const s = data.series;
    if (!s?.CPU_USAGE) { this.railwayError = 'No hay datos'; return; }

    const ts = this.timestamps(s.CPU_USAGE);

    // CPU
    const cpuVals = s.CPU_USAGE.map((v: any) => +(v.value).toFixed(3));
    this.cpuChartData = { labels: ts, datasets: [{ label: 'vCPU', data: cpuVals, borderColor: 'rgb(59, 130, 246)', backgroundColor: 'rgba(59,130,246,0.1)', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 }] };
    this.cpuChartOptions = this.lineOptions(cpuVals, 'vCPU');
    this.cpuChartRef?.update();

    // Memory
    if (s.MEMORY_USAGE_GB?.length) {
      const memVals = s.MEMORY_USAGE_GB.map((v: any) => +(v.value).toFixed(3));
      this.memChartData = { labels: ts, datasets: [{ label: 'GB', data: memVals, borderColor: 'rgb(16, 185, 129)', backgroundColor: 'rgba(16,185,129,0.1)', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 }] };
      this.memChartOptions = this.lineOptions(memVals, 'GB');
      this.memChartRef?.update();
    }

    // Network
    if (s.NETWORK_RX_GB?.length) {
      const rx = s.NETWORK_RX_GB.map((v: any) => +(v.value).toFixed(3));
      const tx = s.NETWORK_TX_GB?.length ? s.NETWORK_TX_GB.map((v: any) => +(v.value).toFixed(3)) : [];
      const allNet = [...rx, ...tx].filter((v: number) => v > 0);
      this.netChartData = {
        labels: ts,
          datasets: [
            { label: 'RX (GB)', data: rx, borderColor: 'rgb(139, 92, 246)', backgroundColor: 'rgba(139,92,246,0.1)', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 },
            ...(tx.length ? [{ label: 'TX (GB)', data: tx, borderColor: 'rgb(251, 146, 60)', backgroundColor: 'rgba(251,146,60,0.1)', borderWidth: 2, fill: true, tension: 0.3, pointRadius: 2 }] : []),
        ],
      };
      this.netChartOptions = {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: { legend: { display: true, position: 'top', labels: { usePointStyle: true, padding: 12, font: { size: 10, weight: 700 } } }, tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y} GB` } } },
        scales: { x: { grid: { display: false }, ticks: { maxRotation: 45, font: { size: 9 } } }, y: { beginAtZero: true, suggestedMax: Math.ceil(Math.max(...allNet, 1) * 1.3), grid: { color: 'rgba(0,0,0,0.06)' }, ticks: { font: { size: 10 }, callback: (v) => `${v} GB` } } },
      };
      this.netChartRef?.update();
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
