import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink, RouterModule } from '@angular/router';
import axiosInstance from '../../../../axiosConfig';
import { Router } from '@angular/router';

@Component({
  selector: 'app-navbar',
  imports: [CommonModule, RouterModule, RouterLink],
  templateUrl: './navbar.html',
  styleUrl: './navbar.css',
})
export class Navbar {
  @Input() activeContent: string = 'home';
  isMobileMenuOpen: boolean = false;
  categories = [
    {
      name: 'Terapias',
      items: [
        'LECTO-ESCRITURA',
        'CONDUCTUAL',
        'DE LENGUAJE',
        'DE APRENDIZAJE',
        'OCUPACIONAL',
      ],
    },
    {
      name: 'Terapias Integrales',
      items: [
        'AUTISMO (TEA)',
        'TDA',
        'TDAH',
        'SÍNDROME DE DOWN',
        'DISCAPACIDAD INTELECTUAL',
      ],
    },
    {
      name: 'Apoyo Virtual',
      items: [
        'COMUNICACIÓN ORAL',
        'LECTO-ESCRITURA',
        'MATEMÁTICAS',
        'DESARROLLO COGNITIVO',
      ],
    },
    {
      name: 'Material Concreto',
      items: [
        'COMUNICACIÓN ORAL',
        'LECTO-ESCRITURA',
        'MATEMÁTICAS',
        'DESARROLLO COGNITIVO',
      ],
    },
  ];
  correo: string = 'informes@centrojuanpabloii.com';

  toggleMobileMenu(): void {
    this.isMobileMenuOpen = !this.isMobileMenuOpen;
  }

  handleLinkClick(): void {
    this.isMobileMenuOpen = false;
  }
  
  isAuthenticated = localStorage.getItem('isAuthenticated') === 'true';
  constructor(private router: Router) {}

  async logout() {
    await axiosInstance.post('/logout');
    localStorage.clear();
    this.router.navigate(['/login']);
  }
}
