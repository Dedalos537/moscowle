import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-contact',
  standalone: false,
  templateUrl: './contact.html',
  styleUrl: './contact.scss',
})
export class Contact implements OnInit {
  form = {
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    subject: '',
    message: '',
    service_interest: '',
    urgency: 'normal',
  };
  submitting = false;
  success = false;
  error = '';

  constructor(
    private headerService: HeaderService,
    private http: HttpClient
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Contacto',
      subtitle: 'Ponte en contacto con nosotros',
      icon: ['fas', 'envelope'],
    });
  }

  submitForm() {
    this.submitting = true;
    this.error = '';
    this.http.post('/api/public/contact', this.form).subscribe({
      next: () => {
        this.success = true;
        this.submitting = false;
        this.form = { first_name: '', last_name: '', email: '', phone: '', subject: '', message: '', service_interest: '', urgency: 'normal' };
      },
      error: (err) => {
        this.error = err.error?.message || 'Error al enviar el mensaje';
        this.submitting = false;
      },
    });
  }
}
