import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { firstValueFrom } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { AlertService } from '../../../../core/services/alert.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Sede, SedeAnalytics } from '../../../../core/models/sede';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { SedeCard } from './components/sede-card/sede-card';

@Component({
  selector: 'app-sedes',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, SedeCard],
  templateUrl: './sedes.html',
  styleUrl: './sedes.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Sedes implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  sedes: Sede[] = [];
  loading = true;
  searchQuery = '';

  showCreateDrawer = false;
  newSede = { name: '', address: '' };
  createStatus = '';

  showEditDrawer = false;
  editSedeData = { id: 0, name: '', address: '' };
  editStatus = '';

  private subscriptions = new Subscription();

  constructor(
    private headerService: HeaderService,
    private adminService: AdminService,
    private alertService: AlertService,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  get activeCount(): number {
    return this.sedes.filter(s => s.active).length;
  }

  get filteredSedes(): Sede[] {
    if (!this.searchQuery.trim()) return this.sedes;
    const q = this.searchQuery.toLowerCase();
    return this.sedes.filter(s =>
      s.name.toLowerCase().includes(q) ||
      (s.address && s.address.toLowerCase().includes(q))
    );
  }

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Sedes',
      subtitle: 'Administra y analiza tus puntos de atención',
      icon: ['fas', 'map-marker-alt'],
      actionTemplate: this.headerActions
    });
    this.loadSedes();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subscriptions.unsubscribe();
  }

  loadSedes() {
    this.loading = true;
    this.subscriptions.add(
      this.adminService.getSedes().subscribe({
        next: (data) => {
          this.sedes = data;
          this.loading = false;
          this.loadAllAnalytics();
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.alertService.show('Error al cargar sedes', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  private loadAllAnalytics() {
    for (const sede of this.sedes) {
      this.subscriptions.add(
        this.adminService.getSedeAnalytics(sede.id).subscribe({
          next: (res) => {
            if (res.success && res.analytics) {
              sede.stats = res.analytics;
            }
            this.cdr.markForCheck();
          },
          error: () => this.cdr.markForCheck(),
        }),
      );
    }
  }

  openCreateDrawer() {
    this.newSede = { name: '', address: '' };
    this.createStatus = '';
    this.showCreateDrawer = true;
    this.cdr.markForCheck();
  }

  closeCreateDrawer() {
    this.showCreateDrawer = false;
  }

  createSede() {
    if (!this.newSede.name.trim()) {
      this.createStatus = 'El nombre es obligatorio';
      return;
    }
    this.createStatus = 'Creando...';
    this.subscriptions.add(
      this.adminService.createSede(this.newSede).subscribe({
        next: (res) => {
          if (res.success) {
            this.createStatus = 'Sede creada';
            this.alertService.show('Sede creada correctamente', 'success');
            setTimeout(() => {
              this.closeCreateDrawer();
              this.loadSedes();
            }, 1500);
          } else {
            this.createStatus = 'Error: ' + (res.message || '');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.createStatus = 'Error de conexión';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  openEditDrawer(sede: Sede) {
    this.editSedeData = { id: sede.id, name: sede.name, address: sede.address || '' };
    this.editStatus = '';
    this.showEditDrawer = true;
  }

  closeEditDrawer() {
    this.showEditDrawer = false;
  }

  updateSede() {
    if (!this.editSedeData.name.trim()) {
      this.editStatus = 'El nombre es obligatorio';
      return;
    }
    this.editStatus = 'Guardando...';
    this.subscriptions.add(
      this.adminService.updateSede(this.editSedeData.id, {
        name: this.editSedeData.name,
        address: this.editSedeData.address,
      }).subscribe({
        next: (res) => {
          if (res.success) {
            this.editStatus = 'Guardado';
            this.alertService.show('Sede actualizada correctamente', 'success');
            setTimeout(() => {
              this.closeEditDrawer();
              this.loadSedes();
            }, 1500);
          } else {
            this.editStatus = 'Error: ' + (res.message || '');
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.editStatus = 'Error de conexión';
          this.cdr.markForCheck();
        },
      }),
    );
  }

  async toggleActive(sede: Sede) {
    const label = sede.active ? 'desactivar' : 'activar';
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: `${sede.active ? 'Desactivar' : 'Activar'} Sede`,
      message: `¿Estás seguro de ${label} la sede "${sede.name}"?`,
      confirmText: sede.active ? 'Desactivar' : 'Activar',
      variant: 'warning',
      icon: ['fas', sede.active ? 'pause' : 'play'],
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.updateSede(sede.id, { active: !sede.active }).subscribe({
        next: (res) => {
          if (res.success) {
            sede.active = !sede.active;
            this.alertService.show(
              `Sede ${sede.active ? 'activada' : 'desactivada'} correctamente`,
              'success',
            );
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.alertService.show('Error al actualizar sede', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }

  async deleteSede(sede: Sede) {
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Eliminar Sede',
      message: `¿Eliminar la sede "${sede.name}"? Esta acción no se puede deshacer.`,
      confirmText: 'Eliminar',
      variant: 'danger',
      icon: ['fas', 'trash'],
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.updateSede(sede.id, { active: false }).subscribe({
        next: () => {
          this.sedes = this.sedes.filter(s => s.id !== sede.id);
          this.alertService.show('Sede eliminada', 'success');
          this.cdr.markForCheck();
        },
        error: () => {
          this.alertService.show('Error al eliminar sede', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }
}
