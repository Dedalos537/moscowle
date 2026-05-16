import { Component } from '@angular/core';
import { routeAnimations } from '../../animations';

@Component({
  selector: 'app-main-layout',
  standalone: false,
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
  animations: [routeAnimations],
})
export class MainLayout {

  prepareRoute() {
    return;
  }

}
