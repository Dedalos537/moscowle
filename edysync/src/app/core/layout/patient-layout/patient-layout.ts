import { Component, OnInit } from '@angular/core';
import { Router, NavigationStart, NavigationEnd, NavigationCancel, NavigationError } from '@angular/router';
import { routeAnimations } from '../../animations';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-patient-layout',
  standalone: false,
  templateUrl: './patient-layout.html',
  styleUrl: './patient-layout.scss',
  animations: [routeAnimations],
})
export class PatientLayout implements OnInit {
  theme: string = 'light';
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
