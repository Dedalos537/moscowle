import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-contact',
  standalone: false,
  templateUrl: './contact.html',
  styleUrl: './contact.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Contact implements OnInit, OnDestroy {
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
  submitted = false;
  loading = false;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private http: HttpClient,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Contacto',
      subtitle: 'Ponte en contacto con nosotros',
      icon: ['fas', 'envelope'],
    });
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  submitForm() {
    this.submitted = true;
    this.submitting = true;
    this.loading = true;
    this.error = '';
    this.cdr.markForCheck();
    this.subs.add(this.http.post('/api/public/contact', this.form).subscribe({
      next: () => {
        this.success = true;
        this.submitting = false;
        this.loading = false;
        this.form = { first_name: '', last_name: '', email: '', phone: '', subject: '', message: '', service_interest: '', urgency: 'normal' };
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.error?.message || 'Error al enviar el mensaje';
        this.submitting = false;
        this.loading = false;
        this.cdr.markForCheck();
      },
    }));
  }
}
