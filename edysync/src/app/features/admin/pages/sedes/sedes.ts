import { Component, OnInit, OnDestroy, ViewChild, TemplateRef, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { firstValueFrom } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { ToastService } from '../../../../core/services/toast.service';
import { ConfirmService } from '../../../../core/services/confirm.service';
import { Sede, SedeAnalytics } from '../../../../core/models/sede';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Drawer } from '../../../../shared/components/drawer/drawer';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { SedeCard } from './components/sede-card/sede-card';

@Component({
  selector: 'app-sedes',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Spinner, SedeCard, Drawer],
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
    private toastService: ToastService,
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
          this.toastService.show('Error al cargar sedes', 'error');
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
            this.toastService.show('Sede creada correctamente', 'success');
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
            this.toastService.show('Sede actualizada correctamente', 'success');
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
    const activating = !sede.active;
    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: `${activating ? 'Activar' : 'Desactivar'} Sede`,
      message: `¿Estás seguro de ${activating ? 'activar' : 'desactivar'} la sede "${sede.name}"?`,
      confirmText: activating ? 'Activar' : 'Desactivar',
      variant: activating ? 'primary' : 'danger',
      icon: ['fas', activating ? 'play' : 'pause'],
    }));
    if (!confirmed) return;
    this.subscriptions.add(
      this.adminService.updateSede(sede.id, { active: !sede.active }).subscribe({
        next: (res) => {
          if (res.success) {
            this.sedes = this.sedes.map(s => s.id === sede.id ? { ...s, active: !s.active } : s);
            this.toastService.show(
              `Sede ${sede.active ? 'activada' : 'desactivada'} correctamente`,
              'success',
            );
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.toastService.show('Error al actualizar sede', 'error');
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
          this.toastService.show('Sede eliminada', 'success');
          this.cdr.markForCheck();
        },
        error: () => {
          this.toastService.show('Error al eliminar sede', 'error');
          this.cdr.markForCheck();
        },
      }),
    );
  }
}
