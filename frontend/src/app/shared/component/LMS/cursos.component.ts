import { Component, OnInit, ViewEncapsulation } from '@angular/core';
import { Router } from '@angular/router';
import { UiEventService } from '../../services/ui-event.service';
import flatpickr from 'flatpickr';
import axiosInstance from '../../../../axiosConfig';

@Component({
  selector: 'app-cursos',
  templateUrl: './cursos.component.html',
  styleUrls: ['./cursos.component.css'],
  encapsulation: ViewEncapsulation.None
})
export class CursosComponent implements OnInit {

  constructor(private router: Router, private uiEventService: UiEventService) {}

  cursos = [
    {
      nombre: 'Curso 1',
      fecha: '01 Jul 2025',
      titulo: 'Terapia Cognitiva',
      tutorImg: 'assets/images/tutor1.jpg',
      imagen: 'assets/images/curso1.jpg'
    },
    {
      nombre: 'Curso 2',
      fecha: '03 Jul 2025',
      titulo: 'Terapia Familiar',
      tutorImg: 'assets/images/tutor2.jpg',
      imagen: 'assets/images/curso2.jpg'
    },
    {
      nombre: 'Curso 3',
      fecha: '05 Jul 2025',
      titulo: 'Terapia Conductual',
      tutorImg: 'assets/images/tutor3.jpg',
      imagen: 'assets/images/curso3.jpg'
    }
  ];

  ngOnInit(): void {
    const isAuth = localStorage.getItem('isAuthenticated');
    const rol = localStorage.getItem('rol');
    if (!isAuth || rol !== 'USER') {
      this.router.navigate(['/login']);
      return;
    }
    // Validar el token con el backend
    axiosInstance.get('/auth/validate')
      .then(() => {
        // Token válido, continúa con la carga normal
        flatpickr('#calendar', {
          dateFormat: 'd/m/Y',
          allowInput: false,
          onClose: () => {
            const calendar = document.getElementById('calendar') as HTMLInputElement;
            if (calendar) calendar.style.display = 'none';
          }
        });

        const darkMode = localStorage.getItem('dark-mode');
        if (darkMode === 'enabled') this.enableDarkMode();

        this.uiEventService.setupEventListeners();
      })
      .catch(() => {
        // Token inválido, redirige al login
        this.router.navigate(['/login']);;
      });
  }

  irPerfil() {
    this.router.navigate(['/perfil']);
  }

  async logout() {
    await axiosInstance.post('/logout');
    localStorage.clear();
    this.router.navigate(['/login']);
  }

  enableDarkMode(): void {
    const toggleBtn = document.getElementById('toggle-btn');
    toggleBtn?.classList.replace('fa-sun', 'fa-moon');
    document.body.classList.add('dark');
    localStorage.setItem('dark-mode', 'enabled');
  }

  disableDarkMode(): void {
    const toggleBtn = document.getElementById('toggle-btn');
    toggleBtn?.classList.replace('fa-moon', 'fa-sun');
    document.body.classList.remove('dark');
    localStorage.setItem('dark-mode', 'disabled');
  }

  setupEventListeners(): void {
    const body = document.body;
    const toggleBtn = document.getElementById('toggle-btn');
    const userBtn = document.getElementById('user-btn');
    const searchBtn = document.getElementById('search-btn');
    const menuBtn = document.getElementById('menu-btn');
    const closeBtn = document.getElementById('close-btn');
    const notifBtn = document.getElementById('notification-btn');
    const backBtn = document.querySelector('.back-btn');

    const profile = document.querySelector('.header .flex .profile') as HTMLElement;
    const search = document.querySelector('.header .flex .search-form') as HTMLElement;
    const sideBar = document.querySelector('.side-bar') as HTMLElement;
    const notifBar = document.querySelector('.notification-bar') as HTMLElement;

    toggleBtn?.addEventListener('click', () => {
      const darkMode = localStorage.getItem('dark-mode');
      if (darkMode === 'disabled') {
        this.enableDarkMode();
      } else {
        this.disableDarkMode();
      }
    });

    userBtn?.addEventListener('click', () => {
      profile?.classList.toggle('active');
      search?.classList.remove('active');
    });

    searchBtn?.addEventListener('click', () => {
      search?.classList.toggle('active');
      profile?.classList.remove('active');
    });

    menuBtn?.addEventListener('click', () => {
      sideBar?.classList.toggle('active');
      body.classList.toggle('active');
    });

    closeBtn?.addEventListener('click', () => {
      sideBar?.classList.remove('active');
      body.classList.remove('active');
    });

    notifBtn?.addEventListener('click', () => {
      notifBar?.classList.toggle('active');
    });

    backBtn?.addEventListener('click', () => {
      notifBar?.classList.remove('active');
    });

    window.onscroll = () => {
      profile?.classList.remove('active');
      search?.classList.remove('active');

      if (window.innerWidth < 1200) {
        sideBar?.classList.remove('active');
        body.classList.remove('active');
      }
    };
  }
}
