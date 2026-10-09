import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription, interval, startWith } from 'rxjs';

interface ServerStatus {
  at: string;
  host: string;
  cpu: { pct: number | null; cores: number | null; load: number[] | null };
  memory: { total: number; used: number; pct: number; swap_total: number; swap_used: number } | null;
  disks: { label: string; total: number; used: number; pct: number }[];
  uptime: number | null;
  process: { pid: number; rss: number | null; threads: number | null };
  services: { unit: string; label: string; state: string }[];
  checks: { name: string; ok: boolean; detail: string }[];
  cockpit_url: string | null;
}

interface Snapshot {
  taken_at: string;
  cpu_pct: number | null;
  mem_pct: number | null;
  disk_pct: number | null;
  services_down: string[];
}

interface Point {
  x: number;
  y: number;
}

const W = 640;
const H = 180;
const PAD = { l: 36, r: 56, t: 12, b: 24 };

/**
 * Estado del servidor, solo lectura: recursos, servicios, piezas de la app e historial de 24 h guardado en la BD.
 * Para administrar el servidor (terminal, reinicios) se usa Cockpit, que tiene su propio inicio de sesión.
 */
@Component({
  selector: 'app-server-monitor',
  standalone: true,
  imports: [FontAwesomeModule],
  templateUrl: './server-monitor.html',
  styleUrl: './server-monitor.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServerMonitor implements OnInit, OnDestroy {
  private http = inject(HttpClient);
  private sub = new Subscription();

  readonly status = signal<ServerStatus | null>(null);
  readonly history = signal<Snapshot[]>([]);
  readonly error = signal<string | null>(null);
  readonly hours = signal(24);
  readonly hover = signal<number | null>(null);

  readonly W = W;
  readonly H = H;
  readonly PAD = PAD;
  readonly gridY = [0, 25, 50, 75, 100];

  readonly series = computed(() => {
    const snaps = this.history();
    if (snaps.length < 2) return null;
    const t0 = Date.parse(snaps[0].taken_at);
    const t1 = Date.parse(snaps[snaps.length - 1].taken_at);
    const span = Math.max(1, t1 - t0);
    const x = (iso: string) => PAD.l + ((Date.parse(iso) - t0) / span) * (W - PAD.l - PAD.r);
    const y = (v: number) => PAD.t + (1 - v / 100) * (H - PAD.t - PAD.b);
    const line = (key: 'cpu_pct' | 'mem_pct') => {
      const pts: Point[] = snaps.filter((s) => s[key] != null).map((s) => ({ x: x(s.taken_at), y: y(s[key] as number) }));
      return { pts, d: pts.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ') };
    };
    const ticks = [0, 0.5, 1].map((f) => ({ x: PAD.l + f * (W - PAD.l - PAD.r), label: this.clock(new Date(t0 + f * span)) }));
    return { cpu: line('cpu_pct'), mem: line('mem_pct'), ticks, y };
  });

  readonly hovered = computed(() => {
    const i = this.hover();
    const snaps = this.history();
    return i == null || !snaps[i] ? null : snaps[i];
  });

  readonly downServices = computed(() => (this.status()?.services ?? []).filter((s) => s.state !== 'active' && s.state !== 'unknown'));

  readonly downLabels = computed(() => this.downServices().map((s) => s.label).join(', '));

  ngOnInit() {
    // Estado vivo cada 10 s; el historial cada minuto (el servidor guarda una foto cada 5 min).
    this.sub.add(interval(10_000).pipe(startWith(0)).subscribe(() => this.loadStatus()));
    this.sub.add(interval(60_000).pipe(startWith(0)).subscribe(() => this.loadHistory()));
  }

  ngOnDestroy() {
    this.sub.unsubscribe();
  }

  loadStatus() {
    this.http.get<ServerStatus>('/api/server-monitor/status').subscribe({
      next: (s) => {
        this.status.set(s);
        this.error.set(null);
      },
      error: (e) => this.error.set(e?.error?.error || 'No se pudo leer el estado del servidor.'),
    });
  }

  loadHistory() {
    this.http
      .get<{ snapshots: Snapshot[] }>('/api/server-monitor/history', { params: new HttpParams().set('hours', this.hours()) })
      .subscribe({ next: (r) => this.history.set(r.snapshots), error: () => this.history.set([]) });
  }

  setHours(h: number) {
    this.hours.set(h);
    this.loadHistory();
  }

  onMove(ev: MouseEvent) {
    const snaps = this.history();
    if (snaps.length < 2) return;
    const svg = ev.currentTarget as SVGElement;
    const rect = svg.getBoundingClientRect();
    const px = ((ev.clientX - rect.left) / rect.width) * W;
    const t0 = Date.parse(snaps[0].taken_at);
    const span = Math.max(1, Date.parse(snaps[snaps.length - 1].taken_at) - t0);
    const target = t0 + ((px - PAD.l) / (W - PAD.l - PAD.r)) * span;
    let best = 0;
    snaps.forEach((s, i) => {
      if (Math.abs(Date.parse(s.taken_at) - target) < Math.abs(Date.parse(snaps[best].taken_at) - target)) best = i;
    });
    this.hover.set(best);
  }

  hoverX() {
    const s = this.hovered();
    const snaps = this.history();
    if (!s || snaps.length < 2) return 0;
    const t0 = Date.parse(snaps[0].taken_at);
    const span = Math.max(1, Date.parse(snaps[snaps.length - 1].taken_at) - t0);
    return PAD.l + ((Date.parse(s.taken_at) - t0) / span) * (W - PAD.l - PAD.r);
  }

  last(pts: Point[]) {
    return pts[pts.length - 1];
  }

  stateLabel(state: string) {
    return state === 'active' ? 'Activo' : state === 'inactive' ? 'Detenido' : state === 'failed' ? 'Con fallas' : state === 'activating' ? 'Iniciando' : 'Sin dato';
  }

  size(bytes: number | null | undefined) {
    if (bytes == null) return '—';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let v = bytes;
    let i = 0;
    while (v >= 1024 && i < units.length - 1) {
      v /= 1024;
      i++;
    }
    return `${v.toFixed(v >= 10 || i === 0 ? 0 : 1).replace('.', ',')} ${units[i]}`;
  }

  uptime(s: number | null) {
    if (s == null) return '—';
    const d = Math.floor(s / 86400);
    const h = Math.floor((s % 86400) / 3600);
    const m = Math.floor((s % 3600) / 60);
    return d ? `${d} d ${h} h` : h ? `${h} h ${m} min` : `${m} min`;
  }

  clock(d: Date) {
    return d.toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' });
  }

  stamp(iso: string) {
    return new Date(iso).toLocaleString('es-PE', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  }

  level(pct: number | null | undefined) {
    return pct == null ? '' : pct >= 90 ? 'is-critical' : pct >= 75 ? 'is-warn' : '';
  }
}
