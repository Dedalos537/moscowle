import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, TemplateRef, ViewChild } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Router, RouterModule } from '@angular/router';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { TherapistService, PatientInfo } from '../../../../core/services/therapist.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';

@Component({
  selector: 'app-therapist-patients',
  standalone: true,
  imports: [CommonModule, RouterModule, FontAwesomeModule, Spinner],
  templateUrl: './patients.html',
  styleUrl: './patients.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistPatients implements OnInit, OnDestroy {
  @ViewChild('headerActions', { static: true }) headerActions!: TemplateRef<unknown>;
  loading = true;
  error: string | null = null;
  patients: (PatientInfo & { status_label?: string; status_color?: string })[] = [];

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private therapistService: TherapistService,
    private cdr: ChangeDetectorRef,
    private router: Router,
  ) {}

  /** Alta de paciente o grupo: se solicita a la coordinación con el mismo formulario. */
  request(kind: 'patient' | 'group') {
    this.router.navigate(['/therapist/requests'], { queryParams: { new: kind } });
  }

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mis Pacientes',
      subtitle: 'Gestiona tus pacientes asignados',
      icon: ['fas', 'user-group'],
      actionTemplate: this.headerActions,
    });
    this.loadPatients();
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  private loadPatients() {
    this.subs.add(this.therapistService.getPatients().subscribe({
      next: (list) => {
        // Estado real del paciente (antes todos salían «Activo»).
        const labels: Record<string, [string, string]> = {
          active: ['Activo', 'bg-success-container text-success'],
          debtor: ['Con deuda', 'bg-warning-container text-warning'],
          inactive: ['Inactivo', 'bg-surface-container-high text-on-surface-variant'],
          retired: ['Retirado', 'bg-surface-container-high text-on-surface-variant'],
        };
        this.patients = list.map((p) => {
          const [status_label, status_color] = labels[(p as { account_status?: string }).account_status || 'active'] ?? labels['active'];
          return { ...p, status_label, status_color };
        });
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }
}
