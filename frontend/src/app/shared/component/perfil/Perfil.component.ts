import {
  Component,
  OnInit,
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
export class PerfilComponent implements OnInit {
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
        this.checkDarkMode();
        this.uiEventService.setupEventListeners();
      })
      .catch(() => this.router.navigate(['/login']));
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

  
}
