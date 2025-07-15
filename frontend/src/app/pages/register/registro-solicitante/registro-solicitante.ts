import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
  FormBuilder,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';

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

  sendSolicitud(): void {
    if (!this.validar()) return;

    setTimeout(() => {
      this.mensaje = '¡Solicitud enviada correctamente! Pronto será aprobada.';
      this.registroForm.reset();
      this.errores = {};
    }, 2000);
  }
}
