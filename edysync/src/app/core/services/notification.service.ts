import { Injectable, signal, inject, OnDestroy, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subscription, interval, tap } from 'rxjs';
import { NotificationItem, NotificationPreferences, NotificationGroup, NotificationGroupItem } from '../models/notification';
import { AdminService } from './admin.service';
import { ChatService } from './chat.service';
import { AuthService } from './auth.service';

@Injectable({
  providedIn: 'root',
})
export class NotificationService implements OnDestroy {
  private adminService = inject(AdminService);
  private chatService = inject(ChatService);
  private authService = inject(AuthService);
  private http = inject(HttpClient);
  private zone = inject(NgZone);

  // ─── Legacy signals (backward compat) ──────────────────────────────
  notifications = signal<NotificationItem[]>([]);
  unreadCount = signal(0);

  // ─── Group signals (new system) ────────────────────────────────────
  groups = signal<NotificationGroup[]>([]);
  expandedGroupId = signal<number | null>(null);
  groupItems = signal<NotificationGroupItem[]>([]);
  groupItemsLoading = signal(false);
  digestSummary = signal<any>(null);

  preferences = signal<NotificationPreferences | null>(null);
  loading = signal(false);
  socketConnected = signal(false);

  private readonly _defaultPrefs: NotificationPreferences = {
    notifications_enabled: true,
    debt_enabled: true, activity_enabled: true,
    system_enabled: true, alert_enabled: true, payment_enabled: true,
    sound_enabled: true, browser_notifications: false,
    digest_enabled: true, digest_channel: 'both',
  };

  get defaultPrefs(): NotificationPreferences {
    return { ...this._defaultPrefs };
  }

  private subs = new Subscription();
  private pollSub: Subscription | null = null;
  private socketSub: Subscription | null = null;

  constructor() {
    this.authService.currentUser$.subscribe(user => {
      if (user) {
        this.init();
      }
    });
  }

  private init(): void {
    this.fetchCount();
    this.fetchGroups();
    this.fetchPreferences();

    this.subs.add(
      this.chatService.connectionStatus$.subscribe(connected => {
        this.socketConnected.set(connected);
        if (connected) {
          this.stopPolling();
        } else {
          this.startPolling();
        }
      })
    );

    // Handle new socket events — groups come as is_group: true
    this.subs.add(
      this.chatService.notificationEvent$.subscribe(data => {
        this.zone.run(() => {
          if (data.is_group) {
            // Update group in the list
            this._upsertGroup(data);
          } else {
            // Legacy item
            const item: NotificationItem = {
              id: data.id,
              title: data.title || null,
              message: data.message,
              type: data.type || 'info',
              category: data.category || 'system',
              priority: data.priority || 'normal',
              icon: data.icon || null,
              timestamp: data.timestamp,
              link: data.link || null,
            };
            this.notifications.update(n => [item, ...n]);
          }
          this.unreadCount.set(data.unread_count);
          this.playNotificationSound();
          this.tryBrowserNotification(data);
        });
      })
    );
  }

  private _upsertGroup(data: any): void {
    const group: NotificationGroup = {
      id: data.id,
      title: data.title || 'Notificaciones',
      category: data.category || 'system',
      priority: data.priority || 'normal',
      count: data.group_count || data.count || 1,
      summary: data.message || null,
      is_read: false,
      is_collapsed: true,
      ai_summary_generated: false,
      timestamp: data.timestamp,
      last_item_at: new Date().toISOString(),
    };

    this.groups.update(groups => {
      const idx = groups.findIndex(g => g.id === group.id);
      if (idx >= 0) {
        const updated = [...groups];
        updated[idx] = { ...updated[idx], count: group.count, summary: group.summary, priority: group.priority, timestamp: group.timestamp };
        return updated;
      }
      return [group, ...groups];
    });
  }

  playNotificationSound(): void {
    const prefs = this.preferences();
    if (prefs && !prefs.sound_enabled) return;

    const audio = new Audio('assets/sounds/notification.wav');
    audio.volume = 0.5;
    audio.play().catch(() => {});
  }

  private tryBrowserNotification(item: any): void {
    const prefs = this.preferences();
    if (!prefs || !prefs.browser_notifications) return;
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;

    new Notification(item.title || 'EdySync', {
      body: item.message || item.summary,
      icon: '/assets/img/logo.svg',
    });
  }

  requestBrowserPermission(): void {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') return;
    if (Notification.permission === 'denied') return;
    Notification.requestPermission();
  }

  // ─── Groups API ────────────────────────────────────────────────────

  fetchGroups(category?: string): void {
    this.loading.set(true);
    let url = '/api/notifications/groups';
    if (category) url += `?category=${category}`;

    this.adminService.getNotificationGroups(category).subscribe({
      next: (data) => {
        this.groups.set(data || []);
        this.unreadCount.set((data || []).filter((g: NotificationGroup) => !g.is_read).length);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  expandGroup(groupId: number): void {
    if (this.expandedGroupId() === groupId) {
      this.expandedGroupId.set(null);
      this.groupItems.set([]);
      return;
    }
    this.expandedGroupId.set(groupId);
    this.groupItemsLoading.set(true);
    this.adminService.getNotificationGroupItems(groupId).subscribe({
      next: (items) => {
        this.groupItems.set(items || []);
        this.groupItemsLoading.set(false);
      },
      error: () => this.groupItemsLoading.set(false),
    });
  }

  markGroupRead(groupId: number): void {
    this.adminService.markNotificationGroupRead(groupId).subscribe({
      next: () => {
        this.groups.update(groups => groups.map(g =>
          g.id === groupId ? { ...g, is_read: true } : g
        ));
        this.unreadCount.update(c => Math.max(0, c - 1));
      },
    });
  }

  markAllGroupsRead(): void {
    this.adminService.markAllNotificationGroupsRead().subscribe({
      next: () => {
        this.groups.update(groups => groups.map(g => ({ ...g, is_read: true })));
        this.unreadCount.set(0);
      },
    });
  }

  toggleGroupCollapse(groupId: number): void {
    this.adminService.toggleNotificationGroupCollapse(groupId).subscribe({
      next: (res: any) => {
        this.groups.update(groups => groups.map(g =>
          g.id === groupId ? { ...g, is_collapsed: res.is_collapsed } : g
        ));
      },
    });
  }

  deleteGroup(groupId: number): void {
    this.adminService.deleteNotificationGroup(groupId).subscribe({
      next: () => {
        this.groups.update(groups => groups.filter(g => g.id !== groupId));
        this.unreadCount.update(c => Math.max(0, c - 1));
        if (this.expandedGroupId() === groupId) {
          this.expandedGroupId.set(null);
          this.groupItems.set([]);
        }
      },
    });
  }

  fetchGroupsSummary(days: number = 1): void {
    this.adminService.getNotificationGroupsSummary(days).subscribe({
      next: (data) => this.digestSummary.set(data),
    });
  }

  sendTestDigest(): Observable<any> {
    return this.adminService.sendTestNotificationDigest();
  }

  // ─── Legacy compat ─────────────────────────────────────────────────

  fetchNotifications(): void {
    this.fetchGroups();
  }

  fetchCount(): void {
    this.adminService.getNotificationCount().subscribe({
      next: (data) => this.unreadCount.set(data.count),
      error: () => {},
    });
  }

  markAllRead(): void {
    this.markAllGroupsRead();
  }

  markOneRead(id: number): void {
    this.markGroupRead(id);
  }

  fetchPreferences(): void {
    this.adminService.getNotificationPreferences().subscribe({
      next: (data) => this.preferences.set(data),
      error: () => this.preferences.set({ ...this._defaultPrefs }),
    });
  }

  updatePreferences(data: Partial<NotificationPreferences>): Observable<any> {
    return this.adminService.updateNotificationPreferences(data).pipe(
      tap(() => {
        this.preferences.update(p => p ? { ...p, ...data } : { ...this._defaultPrefs, ...data });
      }),
    );
  }

  getNotificationsByCategory(category: string): Observable<NotificationItem[]> {
    return this.adminService.getNotificationsByCategory(category);
  }

  // ─── Polling ───────────────────────────────────────────────────────

  private startPolling(): void {
    this.stopPolling();
    this.pollSub = interval(30000).subscribe(() => {
      this.fetchCount();
      this.fetchGroups();
    });
  }

  private stopPolling(): void {
    this.pollSub?.unsubscribe();
    this.pollSub = null;
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    this.socketSub?.unsubscribe();
    this.stopPolling();
  }
}
