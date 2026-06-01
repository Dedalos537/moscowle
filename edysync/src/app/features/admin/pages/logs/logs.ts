import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { LogViewerService, LogEntry } from '../../../../core/services/log-viewer.service';
import { HeaderService } from '../../../../core/services/header.service';
import { fadeInUp, listStagger } from '../../../../core/animations';
import { interval, Subscription } from 'rxjs';

@Component({
  selector: 'app-admin-logs',
  standalone: false,
  templateUrl: './logs.html',
  styleUrl: './logs.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, listStagger],
})
export class Logs implements OnInit, OnDestroy {
  logs: LogEntry[] = [];
  loading = true;
  error: string | null = null;
  autoRefresh = false;
  levelFilter = '';
  searchQuery = '';
  expandedIndex: number | null = null;
  private refreshSub?: Subscription;
  private subscriptions: Subscription = new Subscription();

  readonly levels = ['', 'ERROR', 'WARNING', 'INFO', 'DEBUG'];

  constructor(
    private logViewer: LogViewerService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Visor de Logs',
      subtitle: 'Registros del servidor en tiempo real',
      icon: ['fas', 'terminal'],
    });
    this.loadLogs();
  }

  ngOnDestroy() {
    this.refreshSub?.unsubscribe();
    this.subscriptions.unsubscribe();
  }

  loadLogs() {
    this.loading = true;
    this.error = null;
    this.subscriptions.add(
      this.logViewer.getLogs(this.levelFilter || undefined, 200, this.searchQuery || undefined).subscribe({
        next: (res) => {
          this.logs = res.logs;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => { this.loading = false; this.error = err.error?.message || err.message || 'Error al cargar logs'; this.cdr.markForCheck(); },
      })
    );
  }

  toggleAutoRefresh() {
    this.autoRefresh = !this.autoRefresh;
    if (this.autoRefresh) {
      this.refreshSub = interval(5000).subscribe(() => this.loadLogs());
    } else {
      this.refreshSub?.unsubscribe();
    }
  }

  setLevel(level: string) {
    this.levelFilter = level;
    this.loadLogs();
  }

  search() {
    this.loadLogs();
  }

  toggleExpand(index: number) {
    this.expandedIndex = this.expandedIndex === index ? null : index;
  }

  levelColor(level: string): string {
    const map: any = {
      ERROR: 'var(--color-error)',
      WARNING: 'var(--color-warning)',
      INFO: 'var(--color-info)',
      DEBUG: 'var(--color-outline)',
      CRITICAL: 'var(--color-error)',
    };
    return map[level] || 'var(--color-on-surface-variant)';
  }
}
