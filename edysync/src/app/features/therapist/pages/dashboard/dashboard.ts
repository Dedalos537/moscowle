import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AlertService } from '../../../../core/services/alert.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-dashboard',
  standalone: false,
  templateUrl: './dashboard.html',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistDashboard implements OnInit {
  loading = true;
  data: any = null;
  currentUser: any = null;

  weeklyReportsPending = false;
  weeklyReportsCount = 0;
  weeklyReportWeekStart = '';
  weeklyReportWeekEnd = '';
  showWeeklyReviewModal = false;
  weeklyReportDetail: any = null;
  weeklyReportDetailLoading = false;

  constructor(
    private http: HttpClient,
    private headerService: HeaderService,
    private auth: AuthService,
    private alertService: AlertService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'EduAudit',
      subtitle: '',
      icon: null
    });

    this.auth.currentUser$.subscribe(u => {
      this.currentUser = u;
    });

    this.http.get('/api/therapist/dashboard').subscribe({
      next: (res: any) => {
        if (res.success) {
          this.data = res.data;
          this.data.topics = this.parseTopics(res.data.planned_text);
        }
        this.loading = false;
        this.checkPendingReports();
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  checkPendingReports() {
    this.http.get('/api/therapist/api/weekly-reports/pending').subscribe({
      next: (res: any) => {
        if (res.success && res.has_pending) {
          this.weeklyReportsPending = true;
          this.weeklyReportsCount = res.reports_count;
          this.weeklyReportWeekStart = res.week_start;
          this.weeklyReportWeekEnd = res.week_end;
          setTimeout(() => {
            this.showWeeklyReviewModal = true;
          }, 2000);
        }
      },
      error: () => {}
    });
  }

  viewWeeklyReports() {
    this.showWeeklyReviewModal = false;
    window.location.href = '/therapist/reports';
  }

  dismissWeeklyReview() {
    this.showWeeklyReviewModal = false;
    this.weeklyReportsPending = false;
  }

  parseTopics(text: string): {name: string, status: string}[] {
    if (!text) return [ {name: 'Introducción', status: 'LOGRADO'}, {name: 'Revisión General', status: 'PENDIENTE'} ];
    const lines = text.split('\\n').filter(l => l.trim().length > 3).slice(0, 4);
    return lines.map((l, i) => ({
      name: l.replace(/^[-\*\d\\.]+ */, '').substring(0, 30),
      status: i === 0 ? 'LOGRADO' : (i === 1 ? 'PARCIAL' : 'PENDIENTE')
    }));
  }
}
