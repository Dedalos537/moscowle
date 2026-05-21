// DCE — Diego Centeno Estuvo Acá
import { Component, OnInit } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-therapist-layout',
  standalone: false,
  templateUrl: './therapist-layout.html',
  styleUrl: './therapist-layout.scss',
  animations: [routeAnimations],
})
export class TherapistLayout implements OnInit {
  theme: string = 'light';
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
    const saved = localStorage.getItem('theme');
    const isDark = document.documentElement.classList.contains('dark');
    if (saved === 'dark' || (!saved && isDark)) {
      this.theme = 'dark';
      document.documentElement.classList.add('dark');
    } else if (saved !== 'dark') {
      document.documentElement.classList.remove('dark');
    }
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
  }
}
