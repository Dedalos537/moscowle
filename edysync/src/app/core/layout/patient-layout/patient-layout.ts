import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError, RouterModule } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';
import { SidebarService } from '../../services/sidebar.service';
import { ThemeService } from '../../services/theme.service';
import { Header } from '../../components/header/header';
import { Spinner } from '../../../shared/components/spinner/spinner';
import { Button } from '../../../shared/components/button/button';

@Component({
  selector: 'app-patient-layout',
  standalone: true,
  imports: [RouterModule, CommonModule, FontAwesomeModule, Header, Spinner, Button],
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
    private themeService: ThemeService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.subs.add(this.themeService.theme$.subscribe(t => {
      this.theme = t;
      this.cdr.markForCheck();
    }));
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
    this.themeService.toggle();
  }
}
