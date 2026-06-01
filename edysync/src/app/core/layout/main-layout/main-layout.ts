import { Component, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { routeAnimations } from '../../animations';

@Component({
  selector: 'app-main-layout',
  standalone: false,
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MainLayout {

  constructor(private cdr: ChangeDetectorRef) {}

  prepareRoute() {
    return;
  }

}
