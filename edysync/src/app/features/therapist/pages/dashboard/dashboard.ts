import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { RecordingService } from '../../../../core/services/recording.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';

interface TopicItem {
  name: string;
  status: string;
  status_label: string;
}

interface EmptyState {
  reason: string;
  message: string | null;
  hint: string;
}

interface DashboardData {
  next_session?: { id: number; title: string; start: string; patient?: string; location?: string };
  agenda: any[];
  today_label: string;
  avg_compliance: number;
  session_topics: { items: TopicItem[]; empty_state: EmptyState | null };
  session_progress: number;
  weekly_progress: { percent: number; completed_sessions: number; audited_sessions: number };
  progress: { label: string; weekly_label: string; description: string };
  pending_reports: { count: number; label: string; badge: string | null };
  academic_progress: { delta: number; label: string; subtitle: string; avg_this_month?: number | null };
  ai_coach: { count: number; label: string; badge: string | null };
}

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
  data: DashboardData | null = null;
  currentUser: any = null;
  error: string | null = null;

  weeklyReportWeekStart = '';
  weeklyReportWeekEnd = '';
  weeklyReportLabel = '';
  showWeeklyReviewModal = false;
  weeklyReportDetail: any = null;

  private subs = new Subscription();

  constructor(
    private http: HttpClient,
    private headerService: HeaderService,
    private auth: AuthService,
    private recordingService: RecordingService,
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

    this.loadDashboard();

    this.subs.add(this.recordingService.auditScore$.subscribe(score => {
      if (score != null && this.data) {
        this.data.session_progress = Math.round(score);
        this.refreshSessionTopics(this.data.next_session?.id);
      }
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  private loadDashboard() {
    this.subs.add(this.http.get('/api/therapist/dashboard').subscribe({
      next: (res: any) => {
        if (res.success) {
          this.data = res.data;
        }
        this.loading = false;
        this.cdr.markForCheck();
        this.checkWeeklyReports();
      },
      error: (err) => {
        this.loading = false;
        this.error = err.message;
        this.cdr.markForCheck();
      }
    }));
  }

  private refreshSessionTopics(sessionId?: number) {
    if (!sessionId || !this.data) return;
    this.subs.add(
      this.http.get(`/api/sessions/${sessionId}/objectives`).subscribe({
        next: (res: any) => {
          if (!res.success || !this.data) return;
          if (res.objectives?.length) {
            this.data.session_topics = {
              items: res.objectives.map((o: TopicItem) => ({
                name: o.name,
                status: o.status,
                status_label: o.status_label,
              })),
              empty_state: null,
            };
          }
          this.cdr.markForCheck();
        },
        error: () => {},
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
    return this.data?.next_session?.title || 'Sin sesión hoy';
  }

  get nextSessionTime(): string {
    return this.data?.next_session?.start || '';
  }

  get nextSessionSubtitle(): string {
    const s = this.data?.next_session;
    if (!s) return 'No hay citas programadas para hoy';
    const parts = [s.location, s.patient].filter(Boolean);
    return parts.join(' • ') || 'Sesión programada';
  }

  get sessionProgress(): number {
    return this.data?.session_progress || 0;
  }

  get weeklyProgress(): number {
    return this.data?.weekly_progress?.percent || 0;
  }

  get sessionDescription(): string {
    return this.data?.progress?.description || '';
  }

  get progressLabel(): string {
    return this.data?.progress?.label || 'Cobertura';
  }

  get weeklyProgressLabel(): string {
    return this.data?.progress?.weekly_label || 'Meta semanal';
  }

  get todayDate(): string {
    return this.data?.today_label || '';
  }

  get agenda(): any[] {
    return this.data?.agenda || [];
  }

  get topics(): TopicItem[] {
    return this.data?.session_topics?.items || [];
  }

  get topicsEmptyState(): EmptyState | null {
    return this.data?.session_topics?.empty_state || null;
  }

  get topicsHint(): string | null {
    const empty = this.topicsEmptyState;
    if (empty?.message) return empty.message;
    if (!this.topics.length && empty?.hint) return empty.hint;
    if (this.topics.length && empty?.hint) return empty.hint;
    return null;
  }

  get reportesCount(): number {
    return this.data?.pending_reports?.count ?? 0;
  }

  get reportesLabel(): string {
    return this.data?.pending_reports?.label || 'Reportes pendientes';
  }

  get reportesBadge(): string | null {
    return this.data?.pending_reports?.badge ?? null;
  }

  get academicDelta(): number {
    return this.data?.academic_progress?.delta ?? 0;
  }

  get academicDeltaLabel(): string {
    const d = this.academicDelta;
    return d > 0 ? `+${d}%` : `${d}%`;
  }

  get academicLabel(): string {
    return this.data?.academic_progress?.subtitle || 'Progreso académico';
  }

  get academicPeriod(): string {
    return this.data?.academic_progress?.label || '';
  }

  get aiCoachCount(): number {
    return this.data?.ai_coach?.count ?? 0;
  }

  get aiCoachLabel(): string {
    return this.data?.ai_coach?.label || 'AI Coach';
  }

  get aiCoachBadge(): string | null {
    return this.data?.ai_coach?.badge ?? null;
  }

  checkWeeklyReports() {
    this.subs.add(this.http.get('/api/therapist/weekly-reports/pending').subscribe({
      next: (res: any) => {
        if (res.success && res.has_pending) {
          this.weeklyReportWeekStart = res.week_start;
          this.weeklyReportWeekEnd = res.week_end;
          this.weeklyReportLabel = res.label || '';
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
  }

  generateWeeklyReport() {
    this.subs.add(this.http.post('/api/therapist/weekly-reports/generate', {}).subscribe({
      next: (res: any) => {
        if (res.success) {
          this.showWeeklyReviewModal = true;
          this.weeklyReportDetail = res.report;
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      }
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
