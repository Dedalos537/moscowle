import { Injectable, signal, inject, OnDestroy, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subscription, interval } from 'rxjs';
import { NotificationItem, NotificationPreferences } from '../models/notification';
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

  notifications = signal<NotificationItem[]>([]);
  unreadCount = signal(0);
  preferences = signal<NotificationPreferences | null>(null);
  loading = signal(false);
  socketConnected = signal(false);

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

    this.subs.add(
      this.chatService.notificationEvent$.subscribe(data => {
        this.zone.run(() => {
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
          this.unreadCount.set(data.unread_count);
          this.playNotificationSound();
          this.tryBrowserNotification(item);
        });
      })
    );
  }

  playNotificationSound(): void {
    const prefs = this.preferences();
    if (prefs && !prefs.sound_enabled) return;

    const audio = new Audio('assets/sounds/notification.wav');
    audio.volume = 0.5;
    audio.play().catch(() => {});
  }

  private tryBrowserNotification(item: NotificationItem): void {
    const prefs = this.preferences();
    if (!prefs || !prefs.browser_notifications) return;
    if (!('Notification' in window)) return;
    if (Notification.permission !== 'granted') return;

    new Notification(item.title || 'EdySync', {
      body: item.message,
      icon: '/assets/img/logo.svg',
    });
  }

  requestBrowserPermission(): void {
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') return;
    if (Notification.permission === 'denied') return;
    Notification.requestPermission();
  }

  fetchNotifications(): void {
    this.loading.set(true);
    this.adminService.getNotifications().subscribe({
      next: (data) => {
        this.notifications.set(data || []);
        this.unreadCount.set(data?.length || 0);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  fetchCount(): void {
    this.adminService.getNotificationCount().subscribe({
      next: (data) => this.unreadCount.set(data.count),
      error: () => {},
    });
  }

  markAllRead(): void {
    this.adminService.markNotificationsRead().subscribe({
      next: () => {
        this.notifications.set([]);
        this.unreadCount.set(0);
      },
    });
  }

  markOneRead(id: number): void {
    this.adminService.markOneNotificationRead(id).subscribe({
      next: () => {
        this.notifications.update(n => n.filter(x => x.id !== id));
        this.unreadCount.update(c => Math.max(0, c - 1));
      },
    });
  }

  fetchPreferences(): void {
    this.adminService.getNotificationPreferences().subscribe({
      next: (data) => this.preferences.set(data),
      error: () => {},
    });
  }

  updatePreferences(data: Partial<NotificationPreferences>): Observable<any> {
    const obs = this.adminService.updateNotificationPreferences(data);
    obs.subscribe({
      next: () => {
        this.preferences.update(p => p ? { ...p, ...data } : null);
      },
    });
    return obs;
  }

  getNotificationsByCategory(category: string): Observable<NotificationItem[]> {
    return this.adminService.getNotificationsByCategory(category);
  }

  private startPolling(): void {
    this.stopPolling();
    this.pollSub = interval(60000).subscribe(() => {
      this.fetchCount();
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
