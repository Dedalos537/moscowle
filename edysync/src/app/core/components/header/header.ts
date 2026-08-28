import { Component, OnInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef, effect, ElementRef, HostListener, inject } from '@angular/core';
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
import { Spinner } from '../../../shared/components/spinner/spinner';
import { NotificationService } from '../../services/notification.service';
import { CATEGORY_ICONS, CATEGORY_COLORS, CATEGORY_LABELS, NotificationGroup } from '../../models/notification';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule, FontAwesomeModule, Button, Spinner],
  templateUrl: './header.html',
  styleUrl: './header.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Header implements OnInit, OnDestroy {
  showNotifications = false;
  showUserMenu = false;
  showLogoutWarning = false;

  unreadCount = 0;
  user: any = null;
  isRecording = false;
  error: string | null = null;

  selectedCategory = '';
  availableCategories = ['message', 'session', 'payment', 'alert', 'system'];

  private userSub!: Subscription;
  private recordingSub!: Subscription;
  private subs = new Subscription();

  CATEGORY_ICONS = CATEGORY_ICONS;
  CATEGORY_COLORS = CATEGORY_COLORS;
  CATEGORY_LABELS = CATEGORY_LABELS;

  public headerService = inject(HeaderService);

  private notifEffect = effect(() => {
    this.unreadCount = this.notifService.unreadCount();
    this.cdr.markForCheck();
  });

  constructor(
    private el: ElementRef,
    private adminService: AdminService,
    private authService: AuthService,
    private recordingService: RecordingService,
    private sidebarService: SidebarService,
    private router: Router,
    private confirmService: ConfirmService,
    private cdr: ChangeDetectorRef,
    public notifService: NotificationService,
  ) {}

  @HostListener('document:click', ['$event'])
  onDocumentClick(e: MouseEvent) {
    if (!this.el.nativeElement.contains(e.target)) {
      this.showNotifications = false;
      this.showUserMenu = false;
      this.cdr.markForCheck();
    }
  }

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
    this.notifService.fetchGroups();
  }

  ngOnDestroy() {
    this.userSub?.unsubscribe();
    this.recordingSub?.unsubscribe();
    this.subs.unsubscribe();
  }

  // ─── Notification Group methods ────────────────────────────────────

  notifGroups(): NotificationGroup[] {
    let groups = this.notifService.groups();
    if (this.selectedCategory) {
      groups = groups.filter(g => g.category === this.selectedCategory);
    }
    return groups;
  }

  expandedGroupId(): number | null {
    return this.notifService.expandedGroupId();
  }

  groupItems() {
    return this.notifService.groupItems();
  }

  groupItemsLoading(): boolean {
    return this.notifService.groupItemsLoading();
  }

  loading(): boolean {
    return this.notifService.loading();
  }

  toggleNotifications() {
    this.showNotifications = !this.showNotifications;
    this.showUserMenu = false;
    if (this.showNotifications) {
      this.notifService.fetchGroups();
    }
  }

  filterCategory(category: string) {
    this.selectedCategory = category;
  }

  toggleGroupExpand(groupId: number) {
    this.notifService.expandGroup(groupId);
  }

  markAllAsRead() {
    this.notifService.markAllGroupsRead();
  }

  markGroupAsRead(groupId: number) {
    this.notifService.markGroupRead(groupId);
  }

  toggleUserMenu() {
    this.showUserMenu = !this.showUserMenu;
    this.showNotifications = false;
  }

  isString(value: any): boolean {
    return typeof value === 'string';
  }

  getCatIcon(cat: string): any {
    return (CATEGORY_ICONS as any)[cat] || ['fas', 'bell'];
  }

  getCatColor(cat: string): string {
    return (CATEGORY_COLORS as any)[cat] || 'var(--color-primary-container)';
  }

  getCatLabel(cat: string): string {
    return (CATEGORY_LABELS as any)[cat] || cat;
  }

  getPriorityClass(priority: string): string {
    switch (priority) {
      case 'urgent': return 'bg-error/15 text-error';
      case 'high': return 'bg-warning/15 text-warning';
      case 'normal': return 'bg-surface-container-high text-on-surface-variant';
      case 'low': return 'bg-surface-container-high text-on-surface-variant/60';
      default: return 'bg-surface-container-high text-on-surface-variant';
    }
  }

  getPriorityLabel(priority: string): string {
    switch (priority) {
      case 'urgent': return 'Urgente';
      case 'high': return 'Alta';
      case 'normal': return 'Normal';
      case 'low': return 'Baja';
      default: return priority;
    }
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
