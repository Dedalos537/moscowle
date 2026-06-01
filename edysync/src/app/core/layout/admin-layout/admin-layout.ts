import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { Subscription } from 'rxjs';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-admin-layout',
  standalone: false,
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminLayout implements OnInit, OnDestroy {
  routeLoading = false;
  loadStartTime = 0;
  loadElapsed = '';
  loading = false;
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private router: Router,
    public confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.subs.add(this.router.events.subscribe(e => {
      if (e instanceof NavigationStart) {
        this.routeLoading = true;
        this.loadStartTime = Date.now();
        this.loadElapsed = '';
        this.cdr.markForCheck();
      }
      if (e instanceof NavigationEnd || e instanceof NavigationCancel || e instanceof NavigationError) {
        const elapsed = Date.now() - this.loadStartTime;
        this.loadElapsed = `${(elapsed / 1000).toFixed(1)}s`;
        setTimeout(() => { this.routeLoading = false; this.cdr.markForCheck(); }, 350);
      }
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  prepareRoute() {
    return;
  }

}
