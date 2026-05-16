import { Component, OnInit } from '@angular/core';
import { routeAnimations } from '../../animations';

@Component({
  selector: 'app-therapist-layout',
  standalone: false,
  templateUrl: './therapist-layout.html',
  styleUrl: './therapist-layout.scss',
  animations: [routeAnimations],
})
export class TherapistLayout implements OnInit {
  theme: string = 'light';

  ngOnInit() {
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
