import { Component, OnInit } from '@angular/core';
import axiosInstance from '../../../../axiosConfig';

@Component({
  selector: 'app-contactanos-mensajes',
  templateUrl: './contactanos-mensajes.html',
  styleUrl: './contactanos-mensajes.css'
})
export class ContactanosMensajes implements OnInit {
  mensajes: any[] = [];
  mensaje: string = '';

  async ngOnInit() {
    try {
      const res = await axiosInstance.get('/contactanos');
      this.mensajes = Array.isArray(res.data) ? res.data : [];
    } catch (err: any) {
      this.mensaje = 'Error al cargar mensajes: ' + (err?.response?.data || err.message);
    }
  }
}