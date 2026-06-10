import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FontAwesomeModule } from '@fortawesome/angular-fontawesome';
import { HeaderService } from '../../services/header.service';
import { AdminService } from '../../services/admin.service';
import { AuthService } from '../../services/auth.service';
import { RecordingService } from '../../services/recording.service';
import { SidebarService } from '../../services/sidebar.service';
import { Router } from '@angular/router';
import { Subscription, firstValueFrom } from 'rxjs';
import { ConfirmService } from '../../services/confirm.service';
import { Button } from '../../../shared/components/button/button';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Button],
  templateUrl: './header.html',
  styleUrl: './header.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Header implements OnInit, OnDestroy {
  showNotifications = false;
  showUserMenu = false;
  showLogoutWarning = false;

  notifications: any[] = [];
  unreadCount = 0;
  user: any = null;
  isRecording = false;
  error: string | null = null;
  private userSub!: Subscription;
  private recordingSub!: Subscription;
  private subs = new Subscription();

  constructor(
    public headerService: HeaderService,
    private adminService: AdminService,
    private authService: AuthService,
    private recordingService: RecordingService,
    private sidebarService: SidebarService,
    private router: Router,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
  ) {}

  toggleSidebar() {
    this.sidebarService.toggle();
  }

  ngOnInit() {
    this.userSub = this.authService.currentUser$.subscribe(user => {
      this.user = user;
      this.cdr.markForCheck();
    });
    this.recordingSub = this.recordingService.recordingState$.subscribe(state => {
      this.isRecording = state === 'recording' || state === 'starting' || state === 'mic_error';
      this.cdr.markForCheck();
    });
    this.fetchNotifications();
  }

  ngOnDestroy() {
    this.userSub?.unsubscribe();
    this.recordingSub?.unsubscribe();
    this.subs.unsubscribe();
  }

  toggleNotifications() {
    this.showNotifications = !this.showNotifications;
    this.showUserMenu = false;
    if (this.showNotifications) {
      this.fetchNotifications();
    }
  }

  markAllAsRead() {
    this.subs.add(this.adminService.markNotificationsRead().subscribe({
      next: () => {
        this.unreadCount = 0;
        this.notifications = [];
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
        this.fetchNotifications();
      },
    }));
  }

  markOneRead(notifId: number) {
    this.subs.add(this.adminService.markOneNotificationRead(notifId).subscribe({
      next: () => {
        this.notifications = this.notifications.filter(n => n.id !== notifId);
        this.unreadCount = this.notifications.length;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
        this.fetchNotifications();
      },
    }));
  }

  toggleUserMenu() {
    this.showUserMenu = !this.showUserMenu;
    this.showNotifications = false;
  }

  fetchNotifications() {
    this.subs.add(this.adminService.getNotifications().subscribe({
      next: (data) => {
        this.notifications = data || [];
        this.unreadCount = this.notifications.length;
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.error = err.message;
        this.notifications = [];
        this.unreadCount = 0;
        this.cdr.markForCheck();
      },
    }));
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
    this.subs.add(this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/auth/login'], { queryParams: { logout: 'success' } });
      },
      error: (err) => {
        this.error = err.message;
        this.cdr.markForCheck();
        localStorage.removeItem('user');
        localStorage.removeItem('csrf_token');
        this.router.navigate(['/auth/login'], { queryParams: { logout: 'success' } });
      },
    }));
  }

  cancelLogout() {
    this.showLogoutWarning = false;
  }

}
