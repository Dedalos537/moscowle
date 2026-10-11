import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { GameLibrary } from '../../../../shared/components/game-library/game-library';

/** Juegos (terapeuta): probarlos y ver el nivel de sus pacientes en cada uno. */
@Component({
  selector: 'app-therapist-games',
  standalone: true,
  imports: [GameLibrary],
  template: '<app-game-library mode="therapist" />',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TherapistGames implements OnInit, OnDestroy {
  private header = inject(HeaderService);

  ngOnInit() {
    this.header.setConfig({ title: 'Juegos', subtitle: 'Prueba los juegos y mira el nivel de tus pacientes', icon: ['fas', 'gamepad'] });
  }

  ngOnDestroy() {
    this.header.reset();
  }
}
