import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { AlertService } from '../../../../core/services/alert.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Sede, SedeAnalytics } from '../../../../core/models/sede';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-sedes',
  standalone: false,
  templateUrl: './sedes.html',
  styleUrl: './sedes.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
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

  constructor(
    private headerService: HeaderService,
    private adminService: AdminService,
    private alertService: AlertService,
    private confirmService: ConfirmService,
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
  }

  loadSedes() {
    this.loading = true;
    this.adminService.getSedes().subscribe({
      next: (data) => {
        this.sedes = data;
        this.loading = false;
        this.loadAllAnalytics();
      },
      error: () => {
        this.loading = false;
        this.alertService.show('Error al cargar sedes', 'error');
      },
    });
  }

  private loadAllAnalytics() {
    for (const sede of this.sedes) {
      this.adminService.getSedeAnalytics(sede.id).subscribe({
        next: (res) => {
          if (res.success && res.analytics) {
            sede.stats = res.analytics;
          }
        }
      });
    }
  }

  openCreateDrawer() {
    this.newSede = { name: '', address: '' };
    this.createStatus = '';
    this.showCreateDrawer = true;
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
      },
      error: () => {
        this.createStatus = 'Error de conexión';
      },
    });
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
      },
      error: () => {
        this.editStatus = 'Error de conexión';
      },
    });
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
    this.adminService.updateSede(sede.id, { active: !sede.active }).subscribe({
      next: (res) => {
        if (res.success) {
          sede.active = !sede.active;
          this.alertService.show(
            `Sede ${sede.active ? 'activada' : 'desactivada'} correctamente`,
            'success',
          );
        }
      },
      error: () => this.alertService.show('Error al actualizar sede', 'error'),
    });
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
    this.adminService.updateSede(sede.id, { active: false }).subscribe({
      next: () => {
        this.sedes = this.sedes.filter(s => s.id !== sede.id);
        this.alertService.show('Sede eliminada', 'success');
      },
      error: () => this.alertService.show('Error al eliminar sede', 'error'),
    });
  }
}
