import { Component, OnInit, OnDestroy } from '@angular/core';
import { HeaderService } from '../../services/header.service';
import { AdminService } from '../../services/admin.service';
import { AuthService } from '../../services/auth.service';
import { RecordingService } from '../../services/recording.service';
import { Router } from '@angular/router';
import { Subscription, firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../services/confirm.service';

@Component({
  selector: 'app-header',
  standalone: false,
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header implements OnInit, OnDestroy {
  showNotifications = false;
  showUserMenu = false;
  showLogoutWarning = false;
  notifications: any[] = [];
  unreadCount = 0;
  user: any = null;
  isRecording = false;
  private userSub!: Subscription;
  private recordingSub!: Subscription;

  constructor(
    public headerService: HeaderService,
    private adminService: AdminService,
    private authService: AuthService,
    private recordingService: RecordingService,
    private router: Router,
    private confirmService: ConfirmService,
  ) {}

  ngOnInit() {
    this.userSub = this.authService.currentUser$.subscribe(user => {
      this.user = user;
    });
    this.recordingSub = this.recordingService.recordingState$.subscribe(state => {
      this.isRecording = state === 'recording' || state === 'starting' || state === 'mic_error';
    });
    this.fetchNotifications();
  }

  ngOnDestroy() {
    this.userSub?.unsubscribe();
    this.recordingSub?.unsubscribe();
  }

  toggleNotifications() {
    this.showNotifications = !this.showNotifications;
    this.showUserMenu = false;
    if (this.showNotifications) {
      this.fetchNotifications();
    }
  }

  markAllAsRead() {
    this.adminService.markNotificationsRead().subscribe({
      next: () => {
        this.unreadCount = 0;
        this.notifications = [];
      },
      error: () => {
        this.fetchNotifications();
      },
    });
  }

  markOneRead(notifId: number) {
    this.adminService.markOneNotificationRead(notifId).subscribe({
      next: () => {
        this.notifications = this.notifications.filter(n => n.id !== notifId);
        this.unreadCount = this.notifications.length;
      },
      error: () => {
        this.fetchNotifications();
      },
    });
  }

  toggleUserMenu() {
    this.showUserMenu = !this.showUserMenu;
    this.showNotifications = false;
  }

  fetchNotifications() {
    this.adminService.getNotifications().subscribe({
      next: (data) => {
        this.notifications = data || [];
        this.unreadCount = this.notifications.length;
      },
      error: () => {
        this.notifications = [];
        this.unreadCount = 0;
      },
    });
  }

  isString(value: any): boolean {
    return typeof value === 'string';
  }

  async logout() {
    if (this.isRecording && !this.showLogoutWarning) {
      this.showLogoutWarning = true;
      this.showUserMenu = false;
      return;
    }

    const confirmed = await firstValueFrom(this.confirmService.confirm({
      title: 'Cerrar Sesion',
      message: '¿Estas seguro de que deseas cerrar sesion?',
      confirmText: 'Cerrar Sesion',
      cancelText: 'Cancelar',
      variant: 'danger',
      icon: ['fas', 'sign-out-alt'],
    }));

    if (!confirmed) return;

    this.showLogoutWarning = false;
    this.recordingService.forceStopAndLogout();
    this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/auth/login'], { queryParams: { logout: 'success' } });
      },
      error: () => {
        localStorage.removeItem('user');
        localStorage.removeItem('csrf_token');
        this.router.navigate(['/auth/login'], { queryParams: { logout: 'success' } });
      },
    });
  }

  cancelLogout() {
    this.showLogoutWarning = false;
  }
}
