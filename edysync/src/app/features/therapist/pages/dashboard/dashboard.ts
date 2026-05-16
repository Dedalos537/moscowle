import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
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

  constructor(
    private http: HttpClient,
    private headerService: HeaderService,
    private auth: AuthService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'EduAudit',
      subtitle: '',
      icon: []
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
      },
      error: () => this.loading = false
    });
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
