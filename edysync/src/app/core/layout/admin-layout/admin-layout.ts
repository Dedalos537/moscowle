import { Component } from '@angular/core';
import { routeAnimations } from '../../animations';

@Component({
  selector: 'app-admin-layout',
  standalone: false,
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
  animations: [routeAnimations],
})
export class AdminLayout {

  prepareRoute() {
    return;
  }

}
