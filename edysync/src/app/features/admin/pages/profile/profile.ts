import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { Subscription } from 'rxjs';
import { AdminService } from '../../../../core/services/admin.service';
import { fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter } from '../../../../core/animations';

@Component({
  selector: 'app-profile',
  standalone: false,
  templateUrl: './profile.html',
  styleUrl: './profile.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
  animations: [fadeInUp, fadeInLeft, scaleIn, listStagger, gridStagger, cardEnter]
})
export class Profile implements OnInit, OnDestroy {
  username = '';
  email = '';
  newPassword = '';
  confirmPassword = '';
  saving = false;
  statusText = '';
  statusType: 'success' | 'error' = 'success';
  private subscriptions: Subscription = new Subscription();

  constructor(private admin: AdminService, private cdr: ChangeDetectorRef) {}

  ngOnInit() {
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        const user = JSON.parse(stored);
        this.username = user.username || '';
        this.email = user.email || '';
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
