import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { Subscription } from 'rxjs';
import { AuthService } from '../../../../core/services/auth.service';
import { HeaderService } from '../../../../core/services/header.service';
import { GameLibrary } from '../../../../shared/components/game-library/game-library';

/** Juegos (admin): catálogo, niveles de KPI por paciente, umbrales, fichas y subida (también Clic 3.0). */
@Component({
  selector: 'app-games',
  standalone: true,
  imports: [GameLibrary],
  template: '<app-game-library [mode]="mode()" />',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Games implements OnInit, OnDestroy {
  private header = inject(HeaderService);
  private auth = inject(AuthService);
  private subs = new Subscription();
  readonly mode = signal<'admin' | 'supervisor'>('admin');

  ngOnInit() {
    this.header.setConfig({ title: 'Juegos', subtitle: 'Catálogo, niveles de los pacientes e indicadores', icon: ['fas', 'gamepad'] });
    this.subs.add(this.auth.currentUser$.subscribe((u) => this.mode.set(u?.role === 'supervisor' ? 'supervisor' : 'admin')));
  }

  ngOnDestroy() {
    this.header.reset();
    this.subs.unsubscribe();
  }
}
