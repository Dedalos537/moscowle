import { Component, input, ChangeDetectionStrategy } from '@angular/core';
import { Logo } from '../logo/logo';

@Component({
  selector: 'app-splash-screen',
  standalone: true,
  imports: [Logo, ],
  templateUrl: './splash-screen.html',
  styleUrl: './splash-screen.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SplashScreen {
  isReady = input(false);

}
