import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import axiosInstance from '../../../../axiosConfig';
import { Router } from '@angular/router';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-contactanos-mensajes',
  templateUrl: './contactanos-mensajes.html',
  styleUrl: './contactanos-mensajes.css',
  imports: [CommonModule] 
})

export class ContactanosMensajes implements OnInit {
  mensajes: any[] = [];
  mensaje: string = '';
    constructor(
    private cdr: ChangeDetectorRef,
    private router: Router 
  ) {}

  async ngOnInit() {
    try {
      const res = await axiosInstance.get('/contactanos');
      this.mensajes = Array.isArray(res.data) ? res.data : [];
       this.cdr.detectChanges();
    } catch (err: any) {
      this.mensaje = 'Error al cargar mensajes: ' + (err?.response?.data || err.message);
    }
  }
}