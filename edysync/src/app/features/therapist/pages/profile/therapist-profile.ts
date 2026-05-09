import { Component, OnInit, OnDestroy } from '@angular/core';
import { TherapistService, TherapistProfileData } from '../../../../core/services/therapist.service';
import { HeaderService } from '../../../../core/services/header.service';

@Component({
  selector: 'app-therapist-profile',
  standalone: false,
  templateUrl: './therapist-profile.html',
  styleUrl: './therapist-profile.scss',
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

  constructor(
    private therapistService: TherapistService,
    private headerService: HeaderService,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Perfil',
      subtitle: 'Información personal y configuración',
      icon: ['fas', 'user-circle'],
    });

    this.therapistService.getProfile().subscribe({
      next: (profile) => {
        this.profile = profile;
        this.username = profile.username;
        this.email = profile.email;
        this.timezone = profile.timezone || 'America/Lima';
      },
    });
  }

  ngOnDestroy() {
    this.headerService.reset();
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

    this.therapistService.updateProfile(data).subscribe({
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
      },
      error: () => {
        this.saving = false;
        this.statusType = 'error';
        this.statusText = 'Error de conexión';
      },
    });
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
