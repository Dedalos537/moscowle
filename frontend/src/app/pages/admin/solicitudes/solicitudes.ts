import { CommonModule } from '@angular/common';
import { Component, ChangeDetectorRef } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ContactanosMensajes } from '../contactanos-mensajes/contactanos-mensajes'; 
import axiosInstance from '../../../../axiosConfig';

@Component({
  selector: 'app-solicitudes',
  imports: [CommonModule,ContactanosMensajes],
  templateUrl: './solicitudes.html',
  styleUrl: './solicitudes.css',
})
export class Solicitudes {
  solicitudes: any[] = [];
  mensaje: string = '';

  constructor(
    private cdr: ChangeDetectorRef,
    private router: Router // ✅ ya no usas inject(Router)
  ) {}

  ngOnInit(): void {
    const isAuth = localStorage.getItem('isAuthenticated');
    const rol = localStorage.getItem('rol');
    if (!isAuth || rol !== 'ADMIN') {
      this.router.navigate(['/login']);
      return;
    }
    axiosInstance
      .get('/auth/validate')
      .then(() => {
        this.fetchSolicitudes();
      })
      .catch(() => {
        this.router.navigate(['/login']);
      });
  }

  async fetchSolicitudes(): Promise<void> {
    try {
      const res = await axiosInstance.get('/registro');
      this.solicitudes = Array.isArray(res.data)
        ? res.data
        : res.data.solicitudes || [];
      this.cdr.detectChanges(); // 🔁 Forzar actualización
    } catch (error: any) {
      this.mensaje =
        'Error al cargar solicitudes: ' +
        (error?.response?.data?.message || error.message);
      console.error('Error al cargar solicitudes:', error);
    }
  }

  async aprobar(id: number): Promise<void> {
    try {
      const res = await axiosInstance.put(`/registro/${id}/aprobar`);
      this.mensaje = res.data.message || 'Solicitud aprobada correctamente';
      await this.fetchSolicitudes();
    } catch (error: any) {
      this.mensaje =
        error?.response?.data?.error ||
        error?.response?.data?.message ||
        'No se pudo aprobar la solicitud';
      console.error('Error al aprobar solicitud:', error);
    }
  }

  async handleLogout(): Promise<void> {
    try {
      await axiosInstance.post('/api/logout');
    } catch (e) {}
    localStorage.removeItem('isAuthenticated');
    localStorage.removeItem('rol');
    this.router.navigate(['/login']);
  }

  trackById(index: number, item: any): number {
    return item.id;
  }
}
