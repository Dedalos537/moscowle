import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { HeaderService } from '../../../../core/services/header.service';
import { HttpClient } from '@angular/common/http';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-session-review',
  standalone: false,
  templateUrl: './session-review.html',
  styleUrl: './session-review.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistSessionReview implements OnInit {
  loading = true;
  sessionId!: number;
  session: any = null;
  images: any[] = [];

  constructor(
    private route: ActivatedRoute,
    private headerService: HeaderService,
    private http: HttpClient
  ) {}

  ngOnInit() {
    this.sessionId = Number(this.route.snapshot.paramMap.get('id'));
    this.loadSession();
  }

  private loadSession() {
    this.http.get(`/therapist/appointments/${this.sessionId}/review`).subscribe({
      next: (res: any) => {
        this.session = res.appointment;
        this.images = res.images || [];
        this.headerService.setConfig({
          title: `Revisión: ${res.appointment?.title || 'Sesión'}`,
          subtitle: 'Detalles y evidencias de la sesión',
          icon: ['fas', 'search-plus'],
        });
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }
}
