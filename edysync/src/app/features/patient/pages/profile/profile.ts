import { Component, OnInit } from '@angular/core';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { PatientService } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-profile',
  standalone: false,
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class PatientProfile implements OnInit {
  user: any = null;
  username = '';
  phone = '';
  newPassword = '';
  confirmPassword = '';
  saving = false;
  message = '';
  messageType: 'success' | 'error' = 'success';

  constructor(
    private headerService: HeaderService,
    private authService: AuthService,
    private patientService: PatientService
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Perfil',
      subtitle: 'Gestiona tu información personal',
      icon: ['fas', 'user-circle'],
    });
    this.authService.currentUser$.subscribe((u) => {
      this.user = u;
      if (u) {
        this.username = u.username || '';
        this.phone = u.phone || '';
      }
    });
  }

  saveProfile() {
    this.saving = true;
    this.message = '';
    const payload: any = { username: this.username, phone: this.phone };
    if (this.newPassword && this.newPassword === this.confirmPassword) {
      payload.new_password = this.newPassword;
    }
    this.patientService.updateProfile(payload).subscribe({
      next: (res) => {
        this.saving = false;
        this.messageType = 'success';
        this.message = 'Perfil actualizado correctamente';
        this.newPassword = '';
        this.confirmPassword = '';
      },
      error: () => {
        this.saving = false;
        this.messageType = 'error';
        this.message = 'Error al actualizar el perfil';
      },
    });
  }
}
