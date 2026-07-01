import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HeaderService } from '../../../../core/services/header.service';
import { IncidentService, IncidentDetail } from '../../../../core/services/incident.service';
import { Subscription } from 'rxjs';
import { fadeInUp } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Alert } from '../../../../shared/components/alert/alert';
import { Modal } from '../../../../shared/components/modal/modal';

@Component({
  selector: 'app-incident-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule, FontAwesomeModule, Button, Spinner, Alert, Modal],
  templateUrl: './incident-detail.html',
  styleUrl: './incident-detail.scss',
  animations: [fadeInUp],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class IncidentDetailPage implements OnInit, OnDestroy {
  incident: IncidentDetail | null = null;
  loading = true;
  error: string | null = null;

  // Comment form
  newComment = '';
  isInternal = false;
  submittingComment = false;

  // Status modal
  showStatusModal = false;
  newStatus = '';
  statusComment = '';
  updating = false;

  readonly ESTADOS = ['NUEVO', 'EN_CURSO', 'PENDIENTE_PROVEEDOR', 'RESUELTO', 'CERRADO'];

  private subs = new Subscription();
  private incidentId = 0;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private headerService: HeaderService,
    private incidentService: IncidentService,
    private cdr: inject(ChangeDetectorRef),
  ) {}

  ngOnInit() {
    this.incidentId = Number(this.route.snapshot.paramMap.get('id'));
    this.headerService.setConfig({
      title: `Incidente #${this.incidentId}`,
      subtitle: 'Detalle de incidencia',
      icon: ['fas', 'triangle-exclamation'],
    });
    this.loadIncident();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  loadIncident() {
    this.loading = true;
    this.error = null;
    this.subs.add(
      this.incidentService.getIncident(this.incidentId).subscribe({
        next: (inc) => {
          this.incident = inc;
          this.loading = false;
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.loading = false;
          this.error = err.error?.error || 'Error al cargar incidente';
          this.cdr.markForCheck();
        },
      })
    );
  }

  addComment() {
    if (!this.newComment.trim() || !this.incident) return;
    this.submittingComment = true;
    this.subs.add(
      this.incidentService.addComment(this.incident.id, this.newComment, this.isInternal).subscribe({
        next: () => {
          this.newComment = '';
          this.isInternal = false;
          this.submittingComment = false;
          this.loadIncident();
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.submittingComment = false;
          this.error = err.error?.error || 'Error al agregar comentario';
          this.cdr.markForCheck();
        },
      })
    );
  }

  openStatusModal() {
    if (!this.incident) return;
    this.newStatus = '';
    this.statusComment = '';
    this.showStatusModal = true;
  }

  closeStatusModal() {
    this.showStatusModal = false;
  }

  updateStatus() {
    if (!this.incident || !this.newStatus) return;
    this.updating = true;
    this.subs.add(
      this.incidentService.updateStatus(this.incident.id, this.newStatus, this.statusComment).subscribe({
        next: () => {
          this.updating = false;
          this.showStatusModal = false;
          this.loadIncident();
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

  prioridadLabel(p: number): string {
    const map: Record<number, string> = { 1: 'P1 - Crítica', 2: 'P2 - Alta', 3: 'P3 - Media', 4: 'P4 - Baja' };
    return map[p] || `P${p}`;
  }

  prioridadColor(p: number): string {
    const map: Record<number, string> = { 1: '#dc2626', 2: '#ea580c', 3: '#ca8a04', 4: '#65a30d' };
    return map[p] || '#6b7280';
  }

  estadoColor(e: string): string {
    const map: Record<string, string> = {
      'NUEVO': '#3b82f6', 'EN_CURSO': '#f59e0b', 'PENDIENTE_PROVEEDOR': '#a855f7',
      'RESUELTO': '#22c55e', 'CERRADO': '#6b7280',
    };
    return map[e] || '#6b7280';
  }

  formatDate(dateStr: string | null): string {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleString('es-PE', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  }
}
