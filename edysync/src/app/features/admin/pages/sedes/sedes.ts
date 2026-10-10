import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ElementRef, computed, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription, firstValueFrom } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Scorecard, ScorecardPeriod, Sede } from '../../../../core/models/sede';
import { Drawer } from '../../../../shared/components/drawer/drawer';
import { Button } from '../../../../shared/components/button/button';
import { SedeCard } from './components/sede-card/sede-card';
import { SedeScorecard } from './components/sede-scorecard/sede-scorecard';

interface TargetField {
  key: string;
  label: string;
  unit: string;
  hint: string;
}

@Component({
  selector: 'app-sedes',
  standalone: true,
  imports: [FormsModule, FontAwesomeModule, Button, SedeCard, SedeScorecard, Drawer],
  templateUrl: './sedes.html',
  styleUrl: './sedes.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sedes implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;
  @ViewChild('scorecardAnchor') scorecardAnchor?: ElementRef<HTMLElement>;

  private headerService = inject(HeaderService);
  private adminService = inject(AdminService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);
  private subscriptions = new Subscription();
  private scoreSub?: Subscription;

  readonly periods: { key: ScorecardPeriod; label: string }[] = [
    { key: 'month', label: 'Mes' },
    { key: 'quarter', label: 'Trimestre' },
    { key: 'year', label: 'Año' },
  ];

  readonly sedes = signal<Sede[]>([]);
  readonly loading = signal(true);
  readonly loadError = signal(false);
  readonly searchQuery = signal('');

  readonly period = signal<ScorecardPeriod>('month');
  readonly scorecard = signal<Scorecard | null>(null);
  readonly scoreLoading = signal(true);
  readonly scoreError = signal<string | null>(null);
  /** Sede mostrada en el scorecard; `null` = comparar todas. */
  readonly selectedId = signal<number | null>(null);

  readonly activeCount = computed(() => this.sedes().filter((s) => s.active).length);
  readonly filteredSedes = computed(() => {
    const q = this.searchQuery().trim().toLowerCase();
    // Activas primero; dentro de cada grupo, por nombre.
    const list = [...this.sedes()].sort((a, b) => Number(b.active) - Number(a.active) || a.name.localeCompare(b.name, 'es'));
    if (!q) return list;
    return list.filter((s) => s.name.toLowerCase().includes(q) || (s.address ?? '').toLowerCase().includes(q));
  });
  readonly scoreById = computed(() => new Map((this.scorecard()?.sedes ?? []).map((s) => [s.id, s])));

  // Crear / editar
  readonly showCreateDrawer = signal(false);
  readonly showEditDrawer = signal(false);
  readonly saving = signal(false);
  readonly formError = signal('');
  newSede = { name: '', address: '' };
  editSedeData = { id: 0, name: '', address: '' };

  // Metas del scorecard
  readonly showTargets = signal(false);
  readonly targetGroups = computed(() => {
    const sc = this.scorecard();
    const sample = sc?.sedes[0]?.kpis ?? [];
    return (sc?.perspectives ?? []).map((p) => ({
      label: p.label,
      fields: sample
        .filter((k) => k.perspective === p.key)
        .map<TargetField>((k) => ({
          key: k.key,
          label: k.label,
          unit: k.unit === 'pct' ? '%' : k.unit === 'money' ? 'S/' : '',
          hint: k.direction === 'up' ? 'mínimo' : 'máximo',
        })),
    }));
  });
  targetDraft: Record<string, string> = {};

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Sedes',
      subtitle: 'Puntos de atención y su desempeño',
      icon: ['fas', 'location-dot'],
      actionTemplate: this.headerActions,
    });
    this.loadSedes();
    this.loadScorecard();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
    this.scoreSub?.unsubscribe();
  }

  loadSedes() {
    this.loading.set(true);
    this.loadError.set(false);
    this.subscriptions.add(
      this.adminService.getSedes().subscribe({
        next: (data) => {
          this.sedes.set(data);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.loadError.set(true);
        },
      }),
    );
  }

  loadScorecard() {
    this.scoreSub?.unsubscribe();
    this.scoreLoading.set(true);
    this.scoreError.set(null);
    this.scoreSub = this.adminService.getSedeScorecard(this.period()).subscribe({
      next: (sc) => {
        this.scorecard.set(sc);
        this.scoreLoading.set(false);
        const id = this.selectedId();
        if (id !== null && !sc.sedes.some((s) => s.id === id)) this.selectedId.set(sc.sedes[0]?.id ?? null);
        if (id === null && !this.compareChosen) this.selectedId.set(sc.sedes[0]?.id ?? null);
      },
      error: (e) => {
        this.scoreLoading.set(false);
        this.scoreError.set(e?.error?.message || 'No se pudo calcular el scorecard.');
      },
    });
  }

  private compareChosen = false;

  setPeriod(p: ScorecardPeriod) {
    if (p === this.period()) return;
    this.period.set(p);
    this.loadScorecard();
  }

  chooseSede(id: number | null) {
    this.compareChosen = id === null;
    this.selectedId.set(id);
  }

  /** Tocar una tarjeta muestra esa sede en el scorecard y lleva la vista hasta él. */
  focusSede(sede: Sede) {
    this.chooseSede(sede.id);
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    this.scorecardAnchor?.nativeElement.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  }

  // ── crear / editar ────────────────────────────────────────────────────────
  openCreateDrawer() {
    this.newSede = { name: '', address: '' };
    this.formError.set('');
    this.showCreateDrawer.set(true);
  }

  createSede() {
    const name = this.newSede.name.trim();
    if (!name) return this.formError.set('Escribe el nombre de la sede.');
    this.saving.set(true);
    this.subscriptions.add(
      this.adminService.createSede({ name, address: this.newSede.address.trim() }).subscribe({
        next: (res) => {
          this.saving.set(false);
          if (!res.success) return this.formError.set(res.message === 'Sede ya existe' ? 'Ya existe una sede con ese nombre.' : res.message || 'No se pudo crear la sede.');
          this.showCreateDrawer.set(false);
          this.toastService.show(`Sede «${name}» creada`, 'success');
          this.loadSedes();
          this.loadScorecard();
        },
        error: (e) => {
          this.saving.set(false);
          this.formError.set(e?.error?.message === 'Sede ya existe' ? 'Ya existe una sede con ese nombre.' : 'No se pudo crear la sede. Revisa tu conexión.');
        },
      }),
    );
  }

  openEditDrawer(sede: Sede) {
    this.editSedeData = { id: sede.id, name: sede.name, address: sede.address || '' };
    this.formError.set('');
    this.showEditDrawer.set(true);
  }

  updateSede() {
    const name = this.editSedeData.name.trim();
    if (!name) return this.formError.set('Escribe el nombre de la sede.');
    this.saving.set(true);
    this.subscriptions.add(
      this.adminService.updateSede(this.editSedeData.id, { name, address: this.editSedeData.address.trim() }).subscribe({
        next: (res) => {
          this.saving.set(false);
          if (!res.success) return this.formError.set(res.message || 'No se pudieron guardar los cambios.');
          this.showEditDrawer.set(false);
          this.toastService.show('Cambios guardados', 'success');
          this.loadSedes();
          this.loadScorecard();
        },
        error: () => {
          this.saving.set(false);
          this.formError.set('No se pudieron guardar los cambios. Revisa tu conexión.');
        },
      }),
    );
  }

  async toggleActive(sede: Sede) {
    const activating = !sede.active;
    const confirmed = await firstValueFrom(
      this.confirmService.confirm({
        title: activating ? 'Activar sede' : 'Desactivar sede',
        message: activating
          ? `«${sede.name}» volverá a aparecer al asignar pacientes y en el scorecard.`
          : `«${sede.name}» dejará de aparecer al asignar pacientes y en el scorecard. Sus datos se conservan.`,
        confirmText: activating ? 'Activar' : 'Desactivar',
        variant: activating ? 'primary' : 'danger',
        icon: ['fas', activating ? 'play' : 'pause'],
      }),
    );
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.updateSede(sede.id, { active: activating }).subscribe({
        next: (res) => {
          if (!res.success) return this.toastService.show(res.message || 'No se pudo cambiar el estado de la sede', 'error');
          this.sedes.update((list) => list.map((s) => (s.id === sede.id ? { ...s, active: activating } : s)));
          this.toastService.show(`Sede ${activating ? 'activada' : 'desactivada'}`, 'success');
          this.loadScorecard();
        },
        error: () => this.toastService.show('No se pudo cambiar el estado de la sede', 'error'),
      }),
    );
  }

  // ── metas ─────────────────────────────────────────────────────────────────
  openTargets() {
    const t = this.scorecard()?.targets ?? {};
    this.targetDraft = Object.fromEntries(Object.entries(t).map(([k, v]) => [k, v == null ? '' : String(v)]));
    this.formError.set('');
    this.showTargets.set(true);
  }

  saveTargets() {
    const targets: Record<string, number | null> = {};
    for (const [k, v] of Object.entries(this.targetDraft)) {
      const raw = String(v ?? '').trim().replace(',', '.');
      if (raw === '') targets[k] = null;
      else if (Number.isFinite(Number(raw)) && Number(raw) >= 0) targets[k] = Number(raw);
      else return this.formError.set('Las metas deben ser números positivos o quedar vacías.');
    }
    this.saving.set(true);
    this.subscriptions.add(
      this.adminService.saveScorecardTargets(targets).subscribe({
        next: () => {
          this.saving.set(false);
          this.showTargets.set(false);
          this.toastService.show('Metas guardadas', 'success');
          this.loadScorecard();
        },
        error: (e) => {
          this.saving.set(false);
          this.formError.set(e?.status === 403 ? 'Solo un administrador puede cambiar las metas.' : e?.error?.message || 'No se pudieron guardar las metas.');
        },
      }),
    );
  }
}
