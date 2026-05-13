import { Component, OnInit, OnDestroy, ViewChild, TemplateRef } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { Sede } from '../../../../core/models/sede';

@Component({
  selector: 'app-sedes',
  standalone: false,
  templateUrl: './sedes.html',
  styleUrl: './sedes.scss',
})
export class Sedes implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<any>;

  sedes: Sede[] = [];
  loading = true;

  showCreateDrawer = false;
  newSede = { name: '', address: '' };
  createStatus = '';

  constructor(
    private headerService: HeaderService,
    private adminService: AdminService,
  ) {}

  get activeCount(): number {
    return this.sedes.filter(s => s.active).length;
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
      },
      error: () => (this.loading = false),
    });
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
}
