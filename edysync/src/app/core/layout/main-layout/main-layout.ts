import { Component, ChangeDetectionStrategy } from '@angular/core';
import { RouterModule } from '@angular/router';
import { routeAnimations } from '../../animations';
import { Navbar } from '../navbar/navbar';
import { Footer } from '../footer/footer';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [RouterModule, Navbar, Footer],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MainLayout {

  prepareRoute() {
    return;
  }

}
