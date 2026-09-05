import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HttpClient } from '@angular/common/http';
import { HeaderService } from '../../../../core/services/header.service';
import { AdminService } from '../../../../core/services/admin.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';
import { Button } from '../../../../shared/components/button/button';
import { Modal } from '../../../../shared/components/modal/modal';
import { Input } from '../../../../shared/components/input/input';
import { Select } from '../../../../shared/components/select/select';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-admin-patient-detail',
  standalone: true,
  imports: [CommonModule, RouterModule, FontAwesomeModule, Spinner, Button, Modal, Input, Select, FormsModule],
  templateUrl: './patient-detail.html',
  styleUrl: './patient-detail.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientDetail implements OnInit, OnDestroy {
  loading = true;
  patientId!: number;
  patient: any = null;
  sessions: any[] = [];
  error: string | null = null;

  weeklyReport: any = null;
  weeklyReportLoading = false;
  weeklyReportGenerating = false;

  showSessionModal = false;
  selectedSession: any = null;

  // Patient detail editing
  showEditPatientModal = false;
  patientDetailLoading = false;
  patientDetailSaving = false;
  patientDetailStatus = '';
  patientDetailForm: any = {};

  private subs = new Subscription();

  constructor(
    private route: ActivatedRoute,
    private headerService: HeaderService,
    private adminService: AdminService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.patientId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadPatientData();
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadPatientData() {
    this.loading = true;
    this.error = null;
    this.subs.add(this.http.get(`/therapist/api/patients/${this.patientId}`).subscribe({
      next: (res: any) => {
        this.headerService.setConfig({
          title: res.patient?.username || 'Paciente',
          subtitle: 'Detalle completo del paciente',
          icon: ['fas', 'user'],
        });
        this.patient = res.patient;
        this.sessions = res.recent_sessions || [];
        this.initPatientDetailForm();
        this.loading = false;
        this.cdr.markForCheck();
      },
      error: (err: any) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  private initPatientDetailForm() {
    this.patientDetailForm = {
      document_number: this.patient?.document_number || '',
      phone: this.patient?.phone || '',
      date_of_birth: this.patient?.date_of_birth || '',
      sex: this.patient?.sex || '',
      guardian_name: this.patient?.guardian_name || '',
      guardian_type: this.patient?.guardian_type || '',
      guardian_dni: this.patient?.guardian_dni || '',
      guardian_contact: this.patient?.guardian_contact || '',
      preliminary_diagnosis: this.patient?.preliminary_diagnosis || '',
      therapy_goals: this.patient?.therapy_goals || '',
      notes: this.patient?.notes || '',
      yape_name: this.patient?.yape_name || '',
    };
  }

  viewSession(session: any) {
    this.selectedSession = session;
    this.showSessionModal = true;
    this.cdr.markForCheck();
  }

  closeSessionModal() {
    this.showSessionModal = false;
    this.selectedSession = null;
  }

  generateWeeklyReport() {
    this.weeklyReportGenerating = true;
    this.weeklyReport = null;
    this.cdr.markForCheck();
    const today = new Date();
    const monday = new Date(today.getFullYear(), today.getMonth(), today.getDate() - today.getDay() + 1);
    const weekStart = monday.toISOString().slice(0, 10);
    this.subs.add(this.http.post(`/api/reports/generate-weekly`, { patient_id: this.patientId, week_start: weekStart }).subscribe({
      next: (res: any) => {
        this.weeklyReportGenerating = false;
        if (res.success) {
          this.weeklyReport = res.report;
          this.loadWeeklyReport();
        }
        this.cdr.markForCheck();
      },
      error: (err: any) => {
        this.weeklyReportGenerating = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  loadWeeklyReport() {
    this.weeklyReportLoading = true;
    this.cdr.markForCheck();
    this.subs.add(this.http.get(`/api/reports/weekly/${this.patientId}`).subscribe({
      next: (res: any) => {
        this.weeklyReportLoading = false;
        if (res.success && res.report) {
          this.weeklyReport = res.report;
        }
        this.cdr.markForCheck();
      },
      error: (err: any) => {
        this.weeklyReportLoading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  // Patient detail editing
  openEditPatientModal() {
    this.initPatientDetailForm();
    this.showEditPatientModal = true;
    this.cdr.markForCheck();
  }

  closeEditPatientModal() {
    this.showEditPatientModal = false;
    this.patientDetailStatus = '';
    this.cdr.markForCheck();
  }

  savePatientDetails() {
    this.patientDetailSaving = true;
    this.patientDetailStatus = '';
    this.cdr.markForCheck();

    this.subs.add(this.http.patch(`/admin/api/users/${this.patientId}/patient-details`, this.patientDetailForm).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.patientDetailStatus = 'Guardado correctamente';
          // Update local patient object
          Object.assign(this.patient, this.patientDetailForm);
          this.cdr.markForCheck();
          setTimeout(() => this.closeEditPatientModal(), 1500);
        } else {
          this.patientDetailStatus = res.error || res.message || 'Error al guardar';
        }
        this.patientDetailSaving = false;
        this.cdr.markForCheck();
      },
      error: (err: any) => {
        this.patientDetailStatus = err.error?.error || err.error?.message || err.message || 'Error al guardar';
        this.patientDetailSaving = false;
        this.cdr.markForCheck();
      },
    }));
  }

  cancelEditPatientDetails() {
    this.showEditPatientModal = false;
    this.patientDetailStatus = '';
    this.cdr.markForCheck();
  }
}
