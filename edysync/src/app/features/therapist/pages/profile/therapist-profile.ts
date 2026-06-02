import { CommonModule } from '@angular/common';
import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { TherapistService, TherapistProfileData } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';
import { SelectOption } from '../../../../shared/components/select/select';
import { Card } from '../../../../shared/components/card/card';
import { Input } from '../../../../shared/components/input/input';
import { Select } from '../../../../shared/components/select/select';
import { Alert } from '../../../../shared/components/alert/alert';
import { Button } from '../../../../shared/components/button/button';

@Component({
  selector: 'app-therapist-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule, Card, Input, Select, Alert, Button],
  templateUrl: './therapist-profile.html',
  styleUrl: './therapist-profile.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TherapistProfile implements OnInit, OnDestroy {
  profile: TherapistProfileData | null = null;
  username = '';
  email = '';
  timezone = 'America/Lima';
  newPassword = '';
  confirmPassword = '';
  saving = false;
  statusText = '';
  statusType: 'success' | 'error' = 'success';
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Perfil',
      subtitle: 'Información personal y configuración',
      icon: ['fas', 'user-circle'],
    });

    this.subs.add(this.therapistService.getProfile().subscribe({
      next: (profile) => {
        this.profile = profile;
        this.username = profile.username;
        this.email = profile.email;
        this.timezone = profile.timezone || 'America/Lima';
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
      },
    }));
  }

  ngOnDestroy() {
    this.headerService.reset();
    this.subs.unsubscribe();
  }

  saveProfile() {
    if (this.newPassword && this.newPassword !== this.confirmPassword) {
      this.statusType = 'error';
      this.statusText = 'Las contraseñas no coinciden';
      return;
    }

    this.saving = true;
    this.statusText = '';
    this.cdr.markForCheck();

    const data: any = {};
    if (this.username) data.username = this.username;
    if (this.timezone) data.timezone = this.timezone;
    if (this.newPassword) data.new_password = this.newPassword;

    this.subs.add(this.therapistService.updateProfile(data).subscribe({
      next: (res) => {
        this.saving = false;
        this.statusType = res.success ? 'success' : 'error';
        this.statusText = res.message || (res.success ? 'Perfil actualizado' : 'Error al actualizar');
        if (res.success) {
          this.newPassword = '';
          this.confirmPassword = '';
          const stored = localStorage.getItem('user');
          if (stored) {
            const user = JSON.parse(stored);
            user.username = this.username;
            localStorage.setItem('user', JSON.stringify(user));
          }
        }
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.statusType = 'error';
        this.error = err.message;
        this.statusText = 'Error de conexión';
        this.cdr.markForCheck();
      },
    }));
  }

  get timezoneOptions(): SelectOption[] {
    return this.timezones.map(tz => ({value: tz, label: tz}));
  }

  get timezones(): string[] {
    return [
      'America/Lima',
      'America/New_York',
      'America/Mexico_City',
      'America/Bogota',
      'America/Argentina/Buenos_Aires',
      'America/Santiago',
      'Europe/Madrid',
    ];
  }
}
