import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { Button } from '../../../../shared/components/button/button';
import { Input } from '../../../../shared/components/input/input';
import { Card } from '../../../../shared/components/card/card';
import { Alert } from '../../../../shared/components/alert/alert';

@Component({
  selector: 'app-profile',
  standalone: true,
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  imports: [CommonModule, FormsModule, FontAwesomeModule, Button, Input, Card, Alert],
})
export class Profile implements OnInit, OnDestroy {
  username = '';
  email = '';
  timezone = 'America/Lima';
  newPassword = '';
  confirmPassword = '';
  saving = false;
  statusText = '';
  statusType: 'success' | 'error' = 'success';
  private subscriptions: Subscription = new Subscription();

  readonly timezones = [
    { value: 'America/Lima', label: 'Lima (GMT-5)' },
    { value: 'America/New_York', label: 'Nueva York (GMT-4)' },
    { value: 'America/Mexico_City', label: 'Ciudad de México (GMT-6)' },
    { value: 'America/Bogota', label: 'Bogotá (GMT-5)' },
    { value: 'America/Argentina/Buenos_Aires', label: 'Buenos Aires (GMT-3)' },
    { value: 'America/Santiago', label: 'Santiago (GMT-4)' },
    { value: 'Europe/Madrid', label: 'Madrid (GMT+2)' },
  ];

  constructor(private admin: AdminService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        const user = JSON.parse(stored);
        this.username = user.username || '';
        this.email = user.email || '';
        this.timezone = user.timezone || 'America/Lima';
      } catch {}
    }
  }

  ngOnDestroy() {
    this.subscriptions.unsubscribe();
  }

  saveProfile() {
    if (this.newPassword && this.newPassword !== this.confirmPassword) {
      this.statusType = 'error';
      this.statusText = 'Las contraseñas no coinciden';
      return;
    }
    this.saving = true;
    this.statusText = '';
    const data: any = {};
    if (this.username) data.username = this.username;
    if (this.timezone) data.timezone = this.timezone;
    if (this.newPassword) data.new_password = this.newPassword;
    this.subscriptions.add(
      this.admin.updateProfile(data).subscribe({
        next: (res) => {
          this.saving = false;
          this.statusType = res.success ? 'success' : 'error';
          this.statusText = res.message || (res.success ? 'Perfil actualizado' : 'Error al actualizar');
          if (res.success) {
            this.newPassword = '';
            this.confirmPassword = '';
          }
          this.cdr.markForCheck();
        },
        error: () => {
          this.saving = false;
          this.statusType = 'error';
          this.statusText = 'Error de conexión';
          this.cdr.markForCheck();
        }
      })
    );
  }
}
