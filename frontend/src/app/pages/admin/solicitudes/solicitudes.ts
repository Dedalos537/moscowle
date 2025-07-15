import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-solicitudes',
  imports: [CommonModule],
  templateUrl: './solicitudes.html',
  styleUrl: './solicitudes.css'
})
export class Solicitudes {
 solicitudes = [
    { id: 1, nombre: 'Juan Pérez', correo: 'juan.perez@example.com', servicio: 'Terapia Física', estado: 'PENDIENTE' },
    { id: 2, nombre: 'Ana García', correo: 'ana.garcia@example.com', servicio: 'Terapia Ocupacional', estado: 'PENDIENTE' },
    { id: 3, nombre: 'Carlos López', correo: 'carlos.lopez@example.com', servicio: 'Psicoterapia', estado: 'PENDIENTE' }
  ];

  mensaje: string = '';

  constructor() {}

  ngOnInit(): void {}

  aprobar(id: number): void {
    const solicitud = this.solicitudes.find(s => s.id === id);
    if (solicitud) {
      solicitud.estado = 'APROBADO';
      this.mensaje = 'Solicitud aprobada correctamente';
    }
  }
}
