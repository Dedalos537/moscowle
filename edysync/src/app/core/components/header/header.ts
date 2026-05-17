import { Component, OnInit, OnDestroy } from '@angular/core';
import { HeaderService } from '../../services/header.service';
import { AdminService } from '../../services/admin.service';
import { AuthService } from '../../services/auth.service';
import { RecordingService } from '../../services/recording.service';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';

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
      this.adminService.markNotificationsRead().subscribe(() => {
        this.unreadCount = 0;
      });
    }
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
    });
  }

  isString(value: any): boolean {
    return typeof value === 'string';
  }

  logout() {
    if (this.isRecording && !this.showLogoutWarning) {
      this.showLogoutWarning = true;
      this.showUserMenu = false;
      return;
    }
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
