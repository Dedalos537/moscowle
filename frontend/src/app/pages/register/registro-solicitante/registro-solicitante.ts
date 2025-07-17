import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import axiosInstance from '../../../../axiosConfig';
@Component({
  selector: 'app-registro-solicitante',
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './registro-solicitante.html',
  styleUrl: './registro-solicitante.css',
})
export class RegistroSolicitante {
  registroForm: FormGroup;
  mensaje: string = '';
  errores: any = {};
  features: string[] = [
    'Datos Seguros',
    'Interacción personal y segura',
    'Comunicación Directa',
  ];

  servicios: string[] = [
    'Terapias',
    'Terapias Integrales',
    'Material Virtual',
    'Material Físico',
  ];

  constructor(private fb: FormBuilder) {
    this.registroForm = this.fb.group({
      nombre: ['', Validators.required],
      apellido: ['', Validators.required], // <-- Añade apellido
      correo: ['', [Validators.required, Validators.email]],
      servicio: ['', Validators.required],
    });
  }

  ngOnInit(): void {}

  validar(): boolean {
    this.errores = {};
    if (!this.registroForm.controls['nombre'].valid) {
      this.errores.nombre = true;
    }
    if (!this.registroForm.controls['correo'].valid) {
      this.errores.correo = true;
    }
    if (!this.registroForm.controls['servicio'].valid) {
      this.errores.servicio = true;
    }
    return Object.keys(this.errores).length === 0;
  }

  async sendSolicitud(): Promise<void> {
    if (!this.validar()) return;

    this.mensaje = '';
    this.errores = {};

    try {
      const datos = this.registroForm.value;
      const res = await axiosInstance.post('/registro', datos);
      this.mensaje =
        res.data.message ||
        '¡Solicitud enviada correctamente! Pronto será aprobada.';
      this.registroForm.reset();
    } catch (err: any) {
      this.mensaje =
        err?.response?.data?.error ||
        'Error al enviar la solicitud. Intenta nuevamente.';
    }
  }
}
