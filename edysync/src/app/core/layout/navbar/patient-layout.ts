import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { Subscription } from 'rxjs';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';
import { SidebarService } from '../../services/sidebar.service';

@Component({
  selector: 'app-patient-layout',
  standalone: false,
  templateUrl: './patient-layout.html',
  styleUrl: './patient-layout.scss',
  animations: [routeAnimations],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PatientLayout implements OnInit, OnDestroy {
  theme: string = 'light';
  routeLoading = false;
  loadStartTime = 0;
  loadElapsed = '';
  loading = false;
  error: string | null = null;
  sidebarOpen = false;

  private subs = new Subscription();

  constructor(
    private router: Router,
    public confirmService: ConfirmService,
    public sidebarService: SidebarService,
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
    const saved = localStorage.getItem('theme');
    const isDark = document.documentElement.classList.contains('dark');
    if (saved === 'dark' || (!saved && isDark)) {
      this.theme = 'dark';
      document.documentElement.classList.add('dark');
    } else if (saved !== 'dark') {
      document.documentElement.classList.remove('dark');
    }
    this.subs.add(this.sidebarService.open$.subscribe(open => {
      this.sidebarOpen = open;
      this.cdr.markForCheck();
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  prepareRoute() {
    return;
  }

  toggleDarkMode() {
    this.theme = this.theme === 'light' ? 'dark' : 'light';
    if (this.theme === 'dark') {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
    this.cdr.markForCheck();
  }
}
