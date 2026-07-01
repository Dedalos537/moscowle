import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HeaderService } from '../../../../core/services/header.service';
import { IncidentService, Incident, IncidentDashboard } from '../../../../core/services/incident.service';
import { Subscription } from 'rxjs';
import { fadeInUp, cardEnter, listStagger } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Alert } from '../../../../shared/components/alert/alert';
import { Modal } from '../../../../shared/components/modal/modal';

@Component({
  selector: 'app-incidents',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Button, Spinner, Alert, Modal],
  templateUrl: './incidents.html',
  styleUrl: './incidents.scss',
  animations: [fadeInUp, cardEnter, listStagger],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Incidents implements OnInit, OnDestroy {
  dashboard: IncidentDashboard | null = null;
  incidents: Incident[] = [];
  loading = true;
  error: string | null = null;

  // Filters
  filterEstado = '';
  filterPrioridad: number | null = null;
  filterCategoria = '';
  currentPage = 1;
  totalPages = 1;
  totalItems = 0;

  // Create modal
  showCreateModal = false;
  newIncident = {
    titulo: '',
    descripcion: '',
    categoria: 'SOFTWARE',
    prioridad: 3,
  };
  creating = false;

  // Status change modal
  showStatusModal = false;
  selectedIncident: Incident | null = null;
  newStatus = '';
  statusComment = '';
  updating = false;

  readonly ESTADOS = ['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR', 'RESUELTO', 'CERRADO'];
  readonly CATEGORIAS = ['HARDWARE', 'SOFTWARE', 'RED', 'ACCESOS', 'OPERACIONES'];
  readonly PRIORIDADES = [
    { value: 1, label: 'P1 - Crítica', color: '#dc2626' },
    { value: 2, label: 'P2 - Alta', color: '#ea580c' },
    { value: 3, label: 'P3 - Media', color: '#ca8a04' },
    { value: 4, label: 'P4 - Baja', color: '#65a30d' },
  ];

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private incidentService: IncidentService,
    private cdr: inject(ChangeDetectorRef),
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Incidencias',
      subtitle: 'Gestión y monitoreo de incidencias del sistema',
      icon: ['fas', 'triangle-exclamation'],
    });
    this.loadData();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  loadData() {
    this.loading = true;
    this.error = null;

    this.subs.add(
      this.incidentService.getDashboard().subscribe({
        next: (d) => { this.dashboard = d; this.cdr.markForCheck(); },
        error: () => {},
      })
    );

    this.subs.add(
      this.incidentService.listIncidents({
        estado: this.filterEstado || undefined,
        prioridad: this.filterPrioridad || undefined,
        categoria: this.filterCategoria || undefined,
        page: this.currentPage,
        per_page: 15,
      }).subscribe({
        next: (res) => {
          this.incidents = res.incidentes;
          this.totalPages = res.pages;
          this.totalItems = res.total;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.error || 'Error al cargar incidencias';
          this.cdr.markForCheck();
        },
      })
    );
  }

  applyFilters() {
    this.currentPage = 1;
    this.loadData();
  }

  clearFilters() {
    this.filterEstado = '';
    this.filterPrioridad = null;
    this.filterCategoria = '';
    this.currentPage = 1;
    this.loadData();
  }

  goToPage(page: number) {
    if (page < 1 || page > this.totalPages) return;
    this.currentPage = page;
    this.loadData();
  }

  // --- Create ---
  openCreateModal() {
    this.showCreateModal = true;
    this.newIncident = { titulo: '', descripcion: '', categoria: 'SOFTWARE', prioridad: 3 };
  }

  closeCreateModal() {
    this.showCreateModal = false;
  }

  createIncident() {
    if (!this.newIncident.titulo || !this.newIncident.descripcion) return;
    this.creating = true;
    this.subs.add(
      this.incidentService.createIncident(this.newIncident).subscribe({
        next: () => {
          this.creating = false;
          this.showCreateModal = false;
          this.loadData();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.creating = false;
          this.error = err.error?.error || 'Error al crear incidente';
          this.cdr.markForCheck();
        },
      })
    );
  }

  // --- Status change ---
  openStatusModal(incident: Incident) {
    this.selectedIncident = incident;
    this.newStatus = '';
    this.statusComment = '';
    this.showStatusModal = true;
  }

  closeStatusModal() {
    this.showStatusModal = false;
    this.selectedIncident = null;
  }

  updateStatus() {
    if (!this.selectedIncident || !this.newStatus) return;
    this.updating = true;
    this.subs.add(
      this.incidentService.updateStatus(this.selectedIncident.id, this.newStatus, this.statusComment).subscribe({
        next: () => {
          this.updating = false;
          this.showStatusModal = false;
          this.loadData();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.updating = false;
          this.error = err.error?.error || 'Error al actualizar estado';
          this.cdr.markForCheck();
        },
      })
    );
  }

  getValidTransitions(estado: string): string[] {
    const map: Record<string, string[]> = {
      'NUEVO': ['EN_CURSO', 'PENDIENTE_PROVEEDOR', 'RESUELTO'],
      'EN_CURSO': ['PENDIENTE_PROVEEDOR', 'RESUELTO'],
      'PENDIENTE_PROVEEDOR': ['EN_CURSO', 'RESUELTO'],
      'RESUELTO': ['CERRADO'],
    };
    return map[estado] || [];
  }

  // --- Helpers ---
  prioridadLabel(p: number): string {
    return this.PRIORIDADES.find(x => x.value === p)?.label || `P${p}`;
  }

  prioridadColor(p: number): string {
    return this.PRIORIDADES.find(x => x.value === p)?.color || '#6b7280';
  }

  estadoColor(e: string): string {
    const map: Record<string, string> = {
      'NUEVO': '#3b82f6',
      'EN_CURSO': '#f59e0b',
      'PENDIENTE_PROVEEDOR': '#a855f7',
      'RESUELTO': '#22c55e',
      'CERRADO': '#6b7280',
    };
    return map[e] || '#6b7280';
  }

  categoriaIcon(c: string): string {
    const map: Record<string, string> = {
      'HARDWARE': 'server',
      'SOFTWARE': 'code',
      'RED': 'wifi',
      'ACCESOS': 'lock',
      'OPERACIONES': 'users',
    };
    return map[c] || 'circle';
  }

  timeAgo(dateStr: string | null): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  }
}
