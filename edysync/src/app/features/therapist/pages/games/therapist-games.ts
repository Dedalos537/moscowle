import { Component, OnInit, OnDestroy } from '@angular/core';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-therapist-games',
  standalone: false,
  templateUrl: './therapist-games.html',
  styleUrl: './therapist-games.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class TherapistGames implements OnInit, OnDestroy {
  games: string[] = [];
  loading = false;

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Juegos',
      subtitle: 'Catálogo de juegos disponibles',
      icon: ['fas', 'gamepad'],
    });
    this.loadGames();
  }

  ngOnDestroy() {
    this.headerService.reset();
  }

  private loadGames() {
    this.loading = true;
    this.therapistService.getGames().subscribe({
      next: (res) => {
        this.games = res.games;
        this.loading = false;
      },
      error: () => (this.loading = false),
    });
  }

  getGameUrl(filename: string): string {
    return `/static/games/${filename}`;
  }
}
