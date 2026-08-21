export type NotificationCategory = 'debt' | 'activity' | 'system' | 'alert' | 'payment' | 'audit' | 'reminder';
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';

export const CATEGORY_ICONS: Record<NotificationCategory, string[]> = {
  debt: ['fas', 'money-bill-wave'],
  activity: ['fas', 'calendar-alt'],
  system: ['fas', 'cog'],
  alert: ['fas', 'exclamation-triangle'],
  payment: ['fas', 'credit-card'],
  audit: ['fas', 'clipboard-list'],
  reminder: ['fas', 'bell'],
};

export const CATEGORY_COLORS: Record<NotificationCategory, string> = {
  debt: 'var(--color-warning)',
  activity: 'var(--color-info)',
  system: 'var(--color-primary)',
  alert: 'var(--color-error)',
  payment: 'var(--color-tertiary)',
  audit: 'var(--color-secondary)',
  reminder: 'var(--color-on-surface-variant)',
};

export const CATEGORY_LABELS: Record<NotificationCategory, string> = {
  debt: 'Deudas',
  activity: 'Actividad',
  system: 'Sistema',
  alert: 'Alertas',
  payment: 'Pagos',
  audit: 'Auditoría',
  reminder: 'Recordatorios',
};

export interface NotificationItem {
  id: number;
  title: string | null;
  message: string;
  type: string;
  category: NotificationCategory;
  priority: NotificationPriority;
  icon: string | null;
  timestamp: string;
  link: string | null;
}

export interface NotificationPreferences {
  notifications_enabled: boolean;
  debt_enabled: boolean;
  activity_enabled: boolean;
  system_enabled: boolean;
  alert_enabled: boolean;
  payment_enabled: boolean;
  sound_enabled: boolean;
  browser_notifications: boolean;
}
