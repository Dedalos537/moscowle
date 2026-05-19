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

  constructor(
    private router: Router,
    public confirmService: ConfirmService,
  ) {}

  ngOnInit() {
    this.router.events.subscribe(e => {
      if (e instanceof NavigationStart) this.routeLoading = true;
      if (e instanceof NavigationEnd || e instanceof NavigationCancel || e instanceof NavigationError)
        setTimeout(() => this.routeLoading = false, 300);
    });
  }

  prepareRoute() {
    return;
  }

}
