import { Component, OnInit, OnDestroy } from '@angular/core';
import { HeaderService } from '../../services/header.service';
import { AdminService } from '../../services/admin.service';
import { AuthService } from '../../services/auth.service';
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
  notifications: any[] = [];
  unreadCount = 0;
  
  user: any = null;
  private userSub!: Subscription;

  constructor(
    public headerService: HeaderService,
    private adminService: AdminService,
    private authService: AuthService,
    private router: Router
  ) {}

  ngOnInit() {
    this.userSub = this.authService.currentUser$.subscribe(user => {
      this.user = user;
    });
    this.fetchNotifications();
  }

  ngOnDestroy() {
    if (this.userSub) {
      this.userSub.unsubscribe();
    }
  }

  toggleNotifications() {
    this.showNotifications = !this.showNotifications;
    this.showUserMenu = false;
    
    if (this.showNotifications) {
      this.fetchNotifications();
      // Mark as read
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
      }
    });
  }

  logout() {
    this.authService.logout().subscribe({
      next: () => {
        this.router.navigate(['/auth/login']);
      },
      error: (err) => {
        console.error('Logout error:', err);
        // Force navigation even if backend logout fails (e.g. CORS or already logged out)
        localStorage.removeItem('user');
        localStorage.removeItem('csrf_token');
        this.router.navigate(['/auth/login']);
      }
    });
  }
}
