import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import {
  FormControl,
  FormGroup,
  FormsModule,
  NgForm,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { RouterLink, RouterModule } from '@angular/router';
import axiosInstance from '../../../axiosConfig';

@Component({
  selector: 'app-contact',
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    RouterLink,
  ],
  templateUrl: './contact.html',
  styleUrl: './contact.css',
})
export class Contact {
  formDatos: FormGroup;
  message = '';
  messageType: 'success' | 'error' = 'success';
  isLoading = false;

  constructor() {
    this.formDatos = new FormGroup({
      nombre: new FormControl('', [
        Validators.required,
        Validators.maxLength(100),
      ]),
      correo: new FormControl('', [
        Validators.required,
        Validators.email,
        Validators.maxLength(100),
      ]),
      sujeto: new FormControl('', [
        Validators.required,
        Validators.maxLength(200),
      ]),
      mensaje: new FormControl('', [
        Validators.required,
        Validators.maxLength(5000),
      ]),
    });
  }

  async handleSubmit() {
    this.message = '';
    this.messageType = 'success';

    if (this.formDatos.invalid) {
      this.formDatos.markAllAsTouched();
      return;
    }

    this.isLoading = true;

    try {
      const res = await axiosInstance.post('/contactanos', this.formDatos.value);
      if (res.data.success) {
        this.message = res.data.message || 'Mensaje enviado correctamente. ¡Gracias por contactarnos!';
        this.messageType = 'success';
        this.formDatos.reset();
      } else {
        this.message = res.data.message || 'No se pudo enviar el mensaje.';
        this.messageType = 'error';
      }
    } catch (err: any) {
      this.message = err?.response?.data?.message || 'Error al enviar el mensaje. Intenta nuevamente.';
      this.messageType = 'error';
    } finally {
      this.isLoading = false;
    }
  }
}
