import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { RouterLink, RouterModule } from '@angular/router';

@Component({
  selector: 'app-footer',
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    RouterModule,
    RouterLink
  ],
  templateUrl: './footer.html',
  styleUrl: './footer.css'
})
export class Footer {
email: string = '';
  message: string = '';
  showPrivacidad: boolean = false;
  showTerminos: boolean = false;
  correo: string = 'informes@centrojuanpabloii.com';

  services = [
    { label: 'Terapias', target: 'services' },
    { label: 'Terapias Integrales', target: 'services' },
    { label: 'Apoyo Virtual', target: 'services' },
    { label: 'Material Concreto', target: 'services' }
  ];

  sendEmail(event: Event) {
     this.message = '¡Correo enviado con éxito! Pronto nos comunicaremos contigo.';
  }
}
