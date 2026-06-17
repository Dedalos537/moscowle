import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HttpClient } from '@angular/common/http';
import { Subscription, forkJoin } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';

@Component({
  selector: 'app-therapist-dashboard',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Spinner],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistDashboard implements OnInit, OnDestroy {
  loading = true;
  data: any = null;
  currentUser: any = null;
  error: string | null = null;

  weeklyReportsPending = false;
  weeklyReportsCount = 0;
  weeklyReportWeekStart = '';
  weeklyReportWeekEnd = '';
  showWeeklyReviewModal = false;
  weeklyReportDetail: any = null;
  weeklyReportDetailLoading = false;

  private subs = new Subscription();

  constructor(
    private http: HttpClient,
    private headerService: HeaderService,
    private auth: AuthService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'EduAudit',
      subtitle: '',
      icon: null
    });

    this.subs.add(this.auth.currentUser$.subscribe(u => {
      this.currentUser = u;
      this.cdr.markForCheck();
    }));

    this.subs.add(this.http.get('/api/therapist/dashboard').subscribe({
      next: (res: any) => {
        if (res.success) {
          this.data = res.data;
          this.loadProgramForSession();
        }
        this.loading = false;
        this.cdr.markForCheck();
        this.checkPendingReports();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      }
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  loadProgramForSession() {
    const sessionId = this.data?.next_session?.id;
    if (!sessionId) {
      this.data.topics = this.parseTopics(this.data?.planned_text);
      return;
    }

    this.subs.add(
      this.http.get(`/api/sessions/${sessionId}/program`).subscribe({
        next: (res: any) => {
          const text = res.planned_text || this.data?.planned_text || '';
          this.data.topics = this.parseTopics(text);
          this.cdr.markForCheck();
        },
        error: () => {
          this.data.topics = this.parseTopics(this.data?.planned_text);
          this.cdr.markForCheck();
        }
      })
    );
  }

  get firstName(): string {
    if (!this.currentUser?.username) return '';
    return this.currentUser.username.split(' ')[0];
  }

  get compliancePercent(): number {
    return Math.round(this.data?.avg_compliance || 0);
  }

  get nextSessionTitle(): string {
    return this.data?.next_session?.title || 'Sesión de Terapia';
  }

  get nextSessionTime(): string {
    return this.data?.next_session?.start || '';
  }

  get nextSessionSubtitle(): string {
    const s = this.data?.next_session;
    if (!s) return '';
    const parts = [s.location, s.patient].filter(Boolean);
    return parts.join(' • ') || 'Sesión programada';
  }

  get sessionProgress(): number {
    return this.data?.session_progress || 0;
  }

  get sessionDescription(): string {
    const p = this.sessionProgress;
    if (p >= 80) return 'Excelente avance en el módulo actual.';
    if (p >= 50) return 'Buen progreso, continúa con el plan.';
    if (p > 0) return 'Sesión en curso, pendiente de evaluación.';
    return 'Sin datos de progreso aún.';
  }

  get todayDate(): string {
    const d = new Date();
    const day = d.getDate();
    const months = ['ENE', 'FEB', 'MAR', 'ABR', 'MAY', 'JUN', 'JUL', 'AGO', 'SEP', 'OCT', 'NOV', 'DIC'];
    return `${day} ${months[d.getMonth()]}`;
  }

  get agenda(): any[] {
    return this.data?.agenda || [];
  }

  get topics(): { name: string; status: string }[] {
    return this.data?.topics || [];
  }

  get reportesCount(): number {
    return this.weeklyReportsCount || 8;
  }

  checkPendingReports() {
    this.subs.add(this.http.get('/api/therapist/weekly-reports/pending').subscribe({
      next: (res: any) => {
        if (res.success && res.has_pending) {
          this.weeklyReportsPending = true;
          this.weeklyReportsCount = res.reports_count;
          this.weeklyReportWeekStart = res.week_start;
          this.weeklyReportWeekEnd = res.week_end;
          setTimeout(() => {
            this.showWeeklyReviewModal = true;
            this.cdr.markForCheck();
          }, 2000);
        }
        this.cdr.markForCheck();
      },
      error: () => {
        this.cdr.markForCheck();
      }
    }));
  }

  viewWeeklyReports() {
    this.showWeeklyReviewModal = false;
    window.location.href = '/therapist/reports';
  }

  dismissWeeklyReview() {
    this.showWeeklyReviewModal = false;
    this.weeklyReportsPending = false;
  }

  generateWeeklyReport() {
    this.weeklyReportsPending = true;
    this.subs.add(this.http.post('/api/therapist/weekly-reports/generate', {}).subscribe({
      next: (res: any) => {
        this.weeklyReportsPending = false;
        if (res.success) {
          this.showWeeklyReviewModal = true;
          this.weeklyReportDetail = res.report;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.weeklyReportsPending = false;
        this.error = err.message;
        this.cdr.markForCheck();
      }
    }));
  }

  parseTopics(text: string): { name: string; status: string }[] {
    if (!text) return [
      { name: 'Sin programación', status: 'PENDIENTE' }
    ];

    const lines = text.split('\n')
      .map(l => l.replace(/^[-\*\d\\.]+ */, '').trim())
      .filter(l => l.length > 3 && !l.match(/^(docente|integrantes?|alumno|profesor|fecha|índice|contents)/i))
      .slice(0, 4);

    if (lines.length === 0) return [
      { name: 'Sin programación', status: 'PENDIENTE' }
    ];

    return lines.map((l, i) => ({
      name: l.substring(0, 35),
      status: i === 0 ? 'LOGRADO' : (i === 1 ? 'PARCIAL' : 'PENDIENTE')
    }));
  }

  getTopicIcon(status: string): any {
    switch (status) {
      case 'LOGRADO': return ['fas', 'check-circle'];
      case 'PARCIAL': return ['fas', 'exclamation-circle'];
      default: return ['far', 'circle'];
    }
  }
}
