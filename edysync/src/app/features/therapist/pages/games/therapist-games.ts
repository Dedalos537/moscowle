import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { TherapistService } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Spinner } from '../../../../shared/components/spinner/spinner';

@Component({
  selector: 'app-therapist-games',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Spinner],
  templateUrl: './therapist-games.html',
  styleUrl: './therapist-games.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistGames implements OnInit, OnDestroy {
  games: string[] = [];
  loading = false;
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
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
    this.subs.unsubscribe();
  }

  private loadGames() {
    this.loading = true;
    this.cdr.markForCheck();
    this.subs.add(this.therapistService.getGames().subscribe({
      next: (res) => {
        this.games = res.games;
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

  getGameUrl(filename: string): string {
    return `/static/games/${filename}`;
  }
}
