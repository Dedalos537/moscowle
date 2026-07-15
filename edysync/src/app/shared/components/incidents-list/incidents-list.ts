import { Component, OnInit, OnDestroy, Input, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { IncidentService, Incident } from '../../../core/services/incident.service';
import { fadeInUp, cardEnter } from '../../../core/animations';
import { Spinner } from '../spinner/spinner';
import { Alert } from '../alert/alert';

@Component({
  selector: 'app-incidents-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Spinner, Alert],
  template: `
    <div class="space-y-4 animate-fade-in-up" [@fadeInUp]>
      @if (loading) {
        <app-spinner></app-spinner>
      } @else if (error) {
        <app-alert type="error" [message]="error"></app-alert>
      } @else {
        <div class="flex items-center justify-between">
          <p class="text-sm text-on-surface-variant">{{ totalItems }} incidencia(s)</p>
          <button (click)="showCreateModal = true"
                  class="px-4 py-2 bg-primary text-white rounded-xl text-sm font-bold hover:brightness-110 transition-colors flex items-center gap-2">
            <fa-icon [icon]="['fas', 'plus']"></fa-icon> Reportar
          </button>
        </div>

        @if (incidents.length === 0) {
          <div class="text-center py-12 text-on-surface-variant">
            <fa-icon [icon]="['fas', 'check-circle']" class="text-4xl text-success mb-3"></fa-icon>
            <p>No tienes incidencias registradas</p>
          </div>
        } @else {
          <div class="space-y-3">
            @for (inc of incidents; track inc.id) {
              <div class="bg-surface-container-lowest rounded-xl border border-border/30 p-4 hover:border-primary/30 transition-colors cursor-pointer"
                   [routerLink]="['/admin/incidents', inc.id]">
                <div class="flex items-start justify-between gap-3">
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                      <span class="w-2 h-2 rounded-full" [style.background]="estadoColor(inc.estado)"></span>
                      <span class="text-xs font-bold uppercase" [style.color]="estadoColor(inc.estado)">{{ inc.estado }}</span>
                      <span class="text-xs text-on-surface-variant">{{ timeAgo(inc.fecha_creacion) }}</span>
                    </div>
                    <h4 class="text-sm font-bold text-on-surface truncate">{{ inc.titulo }}</h4>
                    <p class="text-xs text-on-surface-variant mt-1 line-clamp-2">{{ inc.descripcion }}</p>
                  </div>
                  <div class="flex flex-col items-end gap-1 shrink-0">
                    <span class="px-2 py-0.5 rounded-full text-xs font-bold text-white" [style.background]="prioridadColor(inc.prioridad)">
                      {{ prioridadLabel(inc.prioridad) }}
                    </span>
                    <span class="text-xs text-on-surface-variant">{{ inc.categoria }}</span>
                  </div>
                </div>
              </div>
            }
          </div>
        }
      }

      @if (showCreateModal) {
        <div class="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm" (click)="showCreateModal = false">
          <div class="bg-surface-container-lowest rounded-xl shadow-soft border border-border/30 max-w-lg w-full p-6 animate-fade-in" (click)="$event.stopPropagation()">
            <h3 class="text-lg font-bold text-on-surface mb-4">Reportar Incidencia</h3>
            <div class="space-y-4">
              <div>
                <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1">Titulo</label>
                <input [(ngModel)]="newIncident.titulo" class="w-full rounded-xl border border-border px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary outline-none">
              </div>
              <div>
                <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1">Descripcion</label>
                <textarea [(ngModel)]="newIncident.descripcion" rows="3" class="w-full rounded-xl border border-border px-4 py-2.5 text-sm focus:ring-2 focus:ring-primary outline-none resize-none"></textarea>
              </div>
              <div class="grid grid-cols-2 gap-3">
                <div>
                  <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1">Categoria</label>
                  <select [(ngModel)]="newIncident.categoria" class="w-full rounded-xl border border-border px-3 py-2.5 text-sm">
                    <option value="SOFTWARE">Software</option>
                    <option value="HARDWARE">Hardware</option>
                    <option value="RED">Red</option>
                    <option value="ACCESOS">Accesos</option>
                    <option value="OPERACIONES">Operaciones</option>
                  </select>
                </div>
                <div>
                  <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1">Impacto</label>
                  <select [(ngModel)]="newIncident.impacto" class="w-full rounded-xl border border-border px-3 py-2.5 text-sm">
                    <option [ngValue]="1">1 - Bajo</option>
                    <option [ngValue]="2">2 - Medio</option>
                    <option [ngValue]="3">3 - Alto</option>
                  </select>
                </div>
              </div>
              <div>
                <label class="block text-xs font-bold text-on-surface-variant uppercase mb-1">Urgencia</label>
                <select [(ngModel)]="newIncident.urgencia" class="w-full rounded-xl border border-border px-3 py-2.5 text-sm">
                  <option [ngValue]="1">1 - Baja</option>
                  <option [ngValue]="2">2 - Media</option>
                  <option [ngValue]="3">3 - Alta</option>
                </select>
              </div>
              <p class="text-xs text-on-surface-variant">Prioridad calculada: <strong>{{ newIncident.impacto * newIncident.urgencia }}</strong> (Impacto x Urgencia)</p>
            </div>
            <div class="flex justify-end gap-3 mt-6">
              <button (click)="showCreateModal = false" class="px-4 py-2 text-sm font-medium text-on-surface-variant hover:text-on-surface transition-colors">Cancelar</button>
              <button (click)="createIncident()" [disabled]="creating || !newIncident.titulo"
                      class="px-4 py-2 bg-primary text-white rounded-xl text-sm font-bold hover:brightness-110 transition-colors disabled:opacity-50">
                @if (creating) { <fa-icon [icon]="['fas', 'spinner']" class="fa-spin"></fa-icon> }
                Crear
              </button>
            </div>
          </div>
        </div>
      }
    </div>
  `,
  animations: [fadeInUp, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IncidentsList implements OnInit, OnDestroy {
  @Input() viewMode: 'therapist' | 'patient' = 'therapist';

  incidents: Incident[] = [];
  loading = true;
  error: string | null = null;
  totalItems = 0;
  currentPage = 1;

  showCreateModal = false;
  newIncident = {
    titulo: '',
    descripcion: '',
    categoria: 'SOFTWARE',
    impacto: 2,
    urgencia: 2,
  };
  creating = false;

  private subs = new Subscription();

  constructor(
    private incidentService: IncidentService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.loadIncidents();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  loadIncidents() {
    this.loading = true;
    this.subs.add(
      this.incidentService.getMyIncidents(this.currentPage).subscribe({
        next: (res) => {
          this.incidents = res.incidentes;
          this.totalItems = res.total;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: () => {
          this.loading = false;
          this.error = 'Error al cargar incidencias';
          this.cdr.markForCheck();
        },
      })
    );
  }

  createIncident() {
    if (!this.newIncident.titulo) return;
    this.creating = true;
    this.subs.add(
      this.incidentService.createIncident({
        titulo: this.newIncident.titulo,
        descripcion: this.newIncident.descripcion,
        categoria: this.newIncident.categoria,
        impacto: this.newIncident.impacto,
        urgencia: this.newIncident.urgencia,
      }).subscribe({
        next: () => {
          this.creating = false;
          this.showCreateModal = false;
          this.newIncident = { titulo: '', descripcion: '', categoria: 'SOFTWARE', impacto: 2, urgencia: 2 };
          this.loadIncidents();
          this.cdr.markForCheck();
        },
        error: () => {
          this.creating = false;
          this.error = 'Error al crear incidencia';
          this.cdr.markForCheck();
        },
      })
    );
  }

  prioridadLabel(p: number): string {
    const map: Record<number, string> = { 1: 'P1', 2: 'P2', 3: 'P3', 4: 'P4', 6: 'P6', 9: 'P9' };
    return map[p] || `P${p}`;
  }

  prioridadColor(p: number): string {
    if (p >= 6) return '#dc2626';
    if (p >= 4) return '#ea580c';
    if (p >= 3) return '#ca8a04';
    return '#65a30d';
  }

  estadoColor(e: string): string {
    const map: Record<string, string> = {
      'NUEVO': '#3b82f6', 'EN_CURSO': '#f59e0b', 'PENDIENTE_PROVEEDOR': '#a855f7',
      'RESUELTO': '#22c55e', 'CERRADO': '#6b7280',
    };
    return map[e] || '#6b7280';
  }

  timeAgo(dateStr: string | null): string {
    if (!dateStr) return '';
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 60) return `${mins}m`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h`;
    return `${Math.floor(hours / 24)}d`;
  }
}
