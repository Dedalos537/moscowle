import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { Subscription } from 'rxjs';
import { HeaderService } from '../../../../core/services/header.service';
import { AuthService } from '../../../../core/services/auth.service';
import { PatientService } from '../../../../core/services/patient.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-patient-profile',
  standalone: true,
  imports: [CommonModule, FormsModule, FontAwesomeModule],
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class PatientProfile implements OnInit, OnDestroy {
  user: any = null;
  username = '';
  phone = '';
  newPassword = '';
  confirmPassword = '';
  saving = false;
  message = '';
  messageType: 'success' | 'error' = 'success';
  error: string | null = null;

  private subs = new Subscription();

  constructor(
    private headerService: HeaderService,
    private authService: AuthService,
    private patientService: PatientService,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit() {
    this.headerService.setConfig({
      title: 'Mi Perfil',
      subtitle: 'Gestiona tu información personal',
      icon: ['fas', 'user-circle'],
    });
    this.subs.add(this.authService.currentUser$.subscribe((u) => {
      this.user = u;
      if (u) {
        this.username = u.username || '';
        this.phone = u.phone || '';
      }
      this.cdr.markForCheck();
    }));
  }

  ngOnDestroy() {
    this.subs.unsubscribe();
  }

  saveProfile() {
    this.saving = true;
    this.message = '';
    this.cdr.markForCheck();
    const payload: any = { username: this.username, phone: this.phone };
    if (this.newPassword && this.newPassword === this.confirmPassword) {
      payload.new_password = this.newPassword;
    }
    this.subs.add(this.patientService.updateProfile(payload).subscribe({
      next: (res) => {
        this.saving = false;
        this.messageType = 'success';
        this.message = 'Perfil actualizado correctamente';
        this.newPassword = '';
        this.confirmPassword = '';
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.saving = false;
        this.messageType = 'error';
        this.error = err.message;
        this.message = 'Error al actualizar el perfil';
        this.cdr.markForCheck();
      },
    }));
  }
}
