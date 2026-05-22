import { Component, OnInit } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-admin-layout',
  standalone: false,
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
  animations: [routeAnimations],
})
export class AdminLayout implements OnInit {
  routeLoading = false;
  loadStartTime = 0;
  loadElapsed = '';

  constructor(
    private router: Router,
    public confirmService: ConfirmService,
  ) {}

  ngOnInit() {
    this.router.events.subscribe(e => {
      if (e instanceof NavigationStart) {
        this.routeLoading = true;
        this.loadStartTime = Date.now();
        this.loadElapsed = '';
      }
      if (e instanceof NavigationEnd || e instanceof NavigationCancel || e instanceof NavigationError) {
        const elapsed = Date.now() - this.loadStartTime;
        this.loadElapsed = `${(elapsed / 1000).toFixed(1)}s`;
        setTimeout(() => this.routeLoading = false, 350);
      }
    });
  }

  prepareRoute() {
    return;
  }

}
