import {
  Component,
  OnInit,
  AfterViewInit,
  ChangeDetectorRef,
  ViewEncapsulation
} from '@angular/core';
import { Router } from '@angular/router';
import { UiEventService } from '../../services/ui-event.service';
import axiosInstance from '../../../../axiosConfig';
import flatpickr from 'flatpickr';

@Component({
  selector: 'app-perfil',
  templateUrl: './perfil.component.html',
  styleUrls: ['./perfil.component.css', '../LMS/cursos.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class PerfilComponent implements OnInit, AfterViewInit {
  today = new Date();
  currentMonth = this.today.getMonth();
  currentYear = this.today.getFullYear();
  nombreCompleto = '';

  events = [
    { date: '2024-10-27', event: 'Tarea 3', color: 'green' },
    { date: '2024-10-30', event: 'Tarea 2', color: 'blue' }
  ];

  constructor(
    private cdr: ChangeDetectorRef,
    private router: Router,
    private uiEventService: UiEventService
  ) {}

  ngOnInit(): void {
    const isAuth = localStorage.getItem('isAuthenticated');
    const rol = localStorage.getItem('rol');
    if (!isAuth || rol !== 'USER') {
    this.router.navigate(['/login']);
    return;
    }


    axiosInstance
      .get('/auth/validate')
      .then(() => {
        return axiosInstance.get('/auth/me');
      })
      .then((res) => {
        const { nombre, apellido } = res.data;
        this.nombreCompleto = `${nombre} ${apellido}`;
        this.cdr.detectChanges();
        this.setupFlatpickr();
        this.checkDarkMode();
        this.uiEventService.setupEventListeners();
      })
      .catch(() => this.router.navigate(['/login']));
  }

  ngAfterViewInit(): void {
    this.generateCalendar(this.currentMonth, this.currentYear);
    this.addCalendarNavigation();
  }

  irPerfil() {
    this.router.navigate(['/perfil']);
  }

  irCursos() {
    this.router.navigate(['/cursos']);
  }
  async logout() {
    await axiosInstance.post('/logout');
    localStorage.clear();
    this.router.navigate(['/login']);
  }

  private setupFlatpickr(): void {
    flatpickr('#calendar', {
      dateFormat: 'd/m/Y',
      allowInput: false,
      onClose: () => {
        const input = document.getElementById('calendar') as HTMLInputElement;
        if (input) input.style.display = 'none';
      }
    });
  }

  private checkDarkMode(): void {
    const darkMode = localStorage.getItem('dark-mode');
    if (darkMode === 'enabled') {
      this.enableDarkMode();
    }
  }

  enableDarkMode(): void {
    document.getElementById('toggle-btn')?.classList.replace('fa-sun', 'fa-moon');
    document.body.classList.add('dark');
    localStorage.setItem('dark-mode', 'enabled');
  }

  disableDarkMode(): void {
    document.getElementById('toggle-btn')?.classList.replace('fa-moon', 'fa-sun');
    document.body.classList.remove('dark');
    localStorage.setItem('dark-mode', 'disabled');
  }

  private addCalendarNavigation(): void {
    document.getElementById('prev')?.addEventListener('click', () => {
      this.currentMonth = this.currentMonth === 0 ? 11 : this.currentMonth - 1;
      if (this.currentMonth === 11) this.currentYear--;
      this.generateCalendar(this.currentMonth, this.currentYear);
    });

    document.getElementById('next')?.addEventListener('click', () => {
      this.currentMonth = this.currentMonth === 11 ? 0 : this.currentMonth + 1;
      if (this.currentMonth === 0) this.currentYear++;
      this.generateCalendar(this.currentMonth, this.currentYear);
    });
  }

  generateCalendar(month: number, year: number): void {
    const container = document.getElementById('dates');
    const monthLabel = document.getElementById('monthYear');
    if (!container || !monthLabel) return;

    container.innerHTML = '';
    const firstDay = new Date(year, month, 1).getDay();
    const totalDays = new Date(year, month + 1, 0).getDate();

    monthLabel.textContent = new Date(year, month).toLocaleString('es-ES', {
      month: 'long',
      year: 'numeric'
    });

    for (let i = 0; i < (firstDay + 6) % 7; i++) {
      const blank = document.createElement('div');
      blank.classList.add('date');
      container.appendChild(blank);
    }

    for (let day = 1; day <= totalDays; day++) {
      const date = new Date(year, month, day);
      const dayEl = document.createElement('div');
      dayEl.classList.add('date');
      dayEl.textContent = day.toString();

      if (
        day === this.today.getDate() &&
        month === this.today.getMonth() &&
        year === this.today.getFullYear()
      ) {
        dayEl.classList.add('today');
      }

      const event = this.events.find(e => e.date === date.toISOString().slice(0, 10));
      if (event) {
        const eEl = document.createElement('div');
        eEl.classList.add('event');
        eEl.textContent = event.event;
        eEl.style.backgroundColor = event.color;
        dayEl.appendChild(eEl);
      }

      container.appendChild(dayEl);
    }
  }
}
