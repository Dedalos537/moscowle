import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
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
import { BotPanel } from '../bot-panel/bot-panel';

type TabId = 'backend' | 'logs' | 'csp' | 'tokens' | 'incidents' | 'llm' | 'bot';

interface PasswordResetRow {
  id: number;
  user_id: number | null;
  email: string;
  status: string;
  created_at: string;
  expires_at: string;
  completed_at: string | null;
  admin_id: number | null;
  admin_decision: string | null;
  decision_at: string | null;
  requester_ip: string | null;
  target_username?: string;
  target_role?: string;
  temp_password?: string;
}

@Component({
  selector: 'app-visor-funcionamiento',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, Input, Alert, Modal, Incidents, BotPanel],
  templateUrl: './visor-funcionamiento.html',
  styleUrl: './visor-funcionamiento.scss',
  animations: [fadeInUp, scaleIn, listStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class VisorFuncionamiento implements OnInit, OnDestroy {
  activeTab: TabId = 'backend';

  private headerService = inject(HeaderService);
  private admin = inject(AdminService);
  private logViewer = inject(LogViewerService);
  private confirmService = inject(ConfirmService);
  private cdr = inject(ChangeDetectorRef);

  private subs = new Subscription();

  // --- Backend status ---
  serverStatus: 'unknown' | 'running' | 'stopped' = 'unknown';
  serverStatusLoading = true;
  serverHost = '127.0.0.1';
  serverPort = 5000;
  restarting = false;
  restartMessage = '';
  restartError = '';

  // --- Password resets (inline) ---
  resets: PasswordResetRow[] = [];
  resetsLoading = false;
  resetsFilter: 'awaiting_approval' | 'approved' | 'rejected' | 'all' = 'awaiting_approval';
  showApprovedModal = false;
  approvedTempPassword = '';
  approvedTargetUser: any = null;

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

  // --- LLM ---
  llmConfig: any = null;
  llmProviders: any = null;
  llmLoading = false;
  llmTesting = false;
  llmError: string | null = null;
  llmSuccess: string | null = null;
  llmEditing = false;
  llmEditKeys: Record<string, string> = { GLM_API_KEY: '', GROQ_API_KEY: '', GEMINI_API_KEY: '' };

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Centro de Operaciones',
      subtitle: 'Métricas, logs y seguridad del sistema',
      icon: ['fas', 'desktop'],
    });
    this.loadServerStatus();
    this.loadPasswordResets();
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
    if (tab === 'llm') {
      this.loadLLMConfig();
    }
  }

  // --- Backend status ---
  loadServerStatus() {
    this.serverStatusLoading = true;
    this.serverStatus = 'unknown';
    this.cdr.markForCheck();

    this.subs.add(
      this.admin.getServerStatus().subscribe({
        next: (res) => {
          this.serverStatus = (res.status as any) || 'unknown';
          this.serverHost = res.host || '127.0.0.1';
          this.serverPort = res.port || 5000;
          this.serverStatusLoading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.serverStatus = 'stopped';
          this.serverStatusLoading = false;
          this.cdr.markForCheck();
        },
      })
    );
  }

  restartServer() {
    this.restarting = true;
    this.restartMessage = '';
    this.restartError = '';
    this.cdr.markForCheck();

    this.subs.add(
      this.admin.restartServer().subscribe({
        next: (res) => {
          this.restarting = false;
          if (res.status === 'started') {
            this.restartMessage = 'Backend iniciado correctamente. Espera unos segundos...';
            this.serverStatus = 'running';
          } else if (res.status === 'already_running') {
            this.restartMessage = 'Backend ya está activo.';
            this.serverStatus = 'running';
          } else {
            this.restartError = res.message || 'No se pudo iniciar el backend.';
          }
          this.cdr.markForCheck();
          // Refresh status after 3s
          setTimeout(() => this.loadServerStatus(), 3000);
        },
        error: (err) => {
          this.restarting = false;
          this.restartError = err.error?.message || err.message || 'Error al reiniciar';
          this.cdr.markForCheck();
        },
      })
    );
  }

  // --- Password resets (inline) ---
  loadPasswordResets() {
    this.resetsLoading = true;
    this.cdr.markForCheck();
    this.subs.add(
      this.admin.listPasswordResets(this.resetsFilter).subscribe({
        next: (res: any) => {
          this.resets = (res.items as PasswordResetRow[]) || [];
          this.resetsLoading = false;
          this.cdr.markForCheck();
        },
        error: () => { this.resetsLoading = false; this.cdr.markForCheck(); },
      })
    );
  }

  switchResetsFilter(f: 'awaiting_approval' | 'approved' | 'rejected' | 'all') {
    this.resetsFilter = f;
    this.loadPasswordResets();
  }

  approveReset(item: PasswordResetRow) {
    if (!confirm(`Aprobar reseteo de contraseña para ${item.target_username || item.email}?`)) return;
    this.subs.add(
      this.admin.approvePasswordReset(item.id).subscribe({
        next: (res: any) => {
          if (res.success) {
            this.approvedTempPassword = res.temp_password || '';
            this.approvedTargetUser = res.target_user || null;
            this.showApprovedModal = true;
            this.loadPasswordResets();
          }
          this.cdr.markForCheck();
        },
        error: () => this.cdr.markForCheck(),
      })
    );
  }

  rejectReset(item: PasswordResetRow) {
    const reason = prompt(`Motivo de rechazo para ${item.target_username || item.email} (opcional):`);
    if (reason === null) return;
    this.subs.add(
      this.admin.rejectPasswordReset(item.id, reason).subscribe({
        next: () => { this.loadPasswordResets(); this.cdr.markForCheck(); },
        error: () => this.cdr.markForCheck(),
      })
    );
  }

  copyPassword() {
    if (this.approvedTempPassword) {
      navigator.clipboard?.writeText(this.approvedTempPassword);
    }
  }

  resetStatusLabel(s: string): string {
    const m: Record<string, string> = {
      awaiting_approval: 'Pendiente', approved: 'Aprobada', rejected: 'Rechazada',
      pending: 'Pendiente', completed: 'Completada', expired: 'Expirada', verified: 'Verificada',
    };
    return m[s] || s;
  }

  resetStatusClass(s: string): string {
    if (s === 'awaiting_approval') return 'bg-warning/15 text-warning border-warning/30';
    if (s === 'approved' || s === 'completed') return 'bg-success/15 text-success border-success/30';
    if (s === 'rejected' || s === 'expired') return 'bg-error/15 text-error border-error/30';
    return 'bg-surface-container-high text-on-surface-variant border-border/30';
  }

  formatResetDate(s: string | null | undefined): string {
    if (!s) return '—';
    try { return new Date(s).toLocaleString('es-PE', { dateStyle: 'short', timeStyle: 'short' }); }
    catch { return s; }
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

  // --- LLM ---
  loadLLMConfig() {
    this.llmLoading = true;
    this.llmError = null;
    const base = (window as any).__apiBaseUrl || '';
    this.subs.add(
      this.admin.getLLMConfig().subscribe({
        next: (res) => { this.llmConfig = res; this.llmLoading = false; this.cdr.markForCheck(); },
        error: (err) => { this.llmLoading = false; this.llmError = err.error?.error || 'Error al cargar config LLM'; this.cdr.markForCheck(); },
      })
    );
  }

  testLLMProviders() {
    this.llmTesting = true;
    this.llmError = null;
    this.llmSuccess = null;
    this.subs.add(
      this.admin.testLLMProviders().subscribe({
        next: (res) => {
          this.llmProviders = res.providers;
          this.llmTesting = false;
          const chain = res.providers?.chain;
          if (chain?.status === 'ok') {
            this.llmSuccess = `Cadena activa: ${chain.provider} (${chain.latency_ms}ms)`;
          }
          this.cdr.markForCheck();
        },
        error: (err) => { this.llmTesting = false; this.llmError = err.error?.error || 'Error al provar LLM'; this.cdr.markForCheck(); },
      })
    );
  }

  startEditLLM() {
    this.llmEditing = true;
    this.llmEditKeys = { GLM_API_KEY: '', GROQ_API_KEY: '', GEMINI_API_KEY: '' };
    this.llmError = null;
    this.llmSuccess = null;
  }

  cancelEditLLM() {
    this.llmEditing = false;
  }

  saveLLMKeys() {
    const payload: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.llmEditKeys)) {
      if (v && v.trim()) {
        payload[k] = v.trim();
      }
    }
    if (!Object.keys(payload).length) {
      this.llmError = 'Ingresa al menos una API key';
      return;
    }
    this.subs.add(
      this.admin.updateLLMConfig(payload).subscribe({
        next: (res) => {
          this.llmEditing = false;
          this.llmSuccess = `Actualizadas: ${res.updated?.join(', ') || 'ninguna'}`;
          this.loadLLMConfig();
          this.testLLMProviders();
        },
        error: (err) => { this.llmError = err.error?.error || 'Error al guardar'; this.cdr.markForCheck(); },
      })
    );
  }

  providerStatusColor(status: string): string {
    if (status === 'ok') return '#22c55e';
    if (status === 'client_null') return '#eab308';
    return '#ef4444';
  }
}
