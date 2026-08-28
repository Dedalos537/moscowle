export type NotificationCategory = 'debt' | 'activity' | 'system' | 'alert' | 'payment' | 'audit' | 'reminder' | 'security' | 'report' | 'message' | 'session' | 'game' | 'contact' | 'user_mgmt';
export type NotificationPriority = 'low' | 'normal' | 'high' | 'urgent';

export const CATEGORY_ICONS: Record<string, [string, string]> = {
  debt: ['fas', 'money-bill-wave'],
  activity: ['fas', 'calendar-check'],
  system: ['fas', 'cog'],
  alert: ['fas', 'triangle-exclamation'],
  payment: ['fas', 'credit-card'],
  audit: ['fas', 'clipboard-check'],
  reminder: ['fas', 'bell'],
  security: ['fas', 'shield-halved'],
  report: ['fas', 'chart-bar'],
  message: ['fas', 'envelope'],
  session: ['fas', 'calendar-alt'],
  game: ['fas', 'gamepad'],
  contact: ['fas', 'phone'],
  user_mgmt: ['fas', 'users'],
};

export const CATEGORY_COLORS: Record<string, string> = {
  debt: 'var(--color-warning)',
  activity: 'var(--color-info)',
  system: 'var(--color-outline)',
  alert: 'var(--color-error)',
  payment: 'var(--color-success)',
  audit: '#8b5cf6',
  reminder: 'var(--color-primary)',
  security: '#ef4444',
  report: '#3b82f6',
  message: '#06b6d4',
  session: '#10b981',
  game: '#f59e0b',
  contact: '#6366f1',
  user_mgmt: '#8b5cf6',
};

export const CATEGORY_LABELS: Record<string, string> = {
  debt: 'Deudas',
  activity: 'Actividad',
  system: 'Sistema',
  alert: 'Alertas',
  payment: 'Pagos',
  audit: 'Auditorías',
  reminder: 'Recordatorios',
  security: 'Seguridad',
  report: 'Reportes',
  message: 'Mensajes',
  session: 'Sesiones',
  game: 'Juegos',
  contact: 'Contacto',
  user_mgmt: 'Usuarios',
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
  count?: number; // Group item count (new system)
}

export interface NotificationGroup {
  id: number;
  title: string;
  category: NotificationCategory;
  priority: NotificationPriority;
  count: number;
  summary: string | null;
  is_read: boolean;
  is_collapsed: boolean;
  ai_summary_generated: boolean;
  timestamp: string;
  last_item_at: string;
}

export interface NotificationGroupItem {
  id: number;
  message: string;
  type: string;
  priority: NotificationPriority;
  icon: string | null;
  link: string | null;
  timestamp: string;
}

export interface NotificationPreferences {
  notifications_enabled?: boolean;
  debt_enabled: boolean;
  activity_enabled: boolean;
  system_enabled: boolean;
  alert_enabled: boolean;
  payment_enabled: boolean;
  sound_enabled: boolean;
  browser_notifications: boolean;
  digest_enabled: boolean;
  digest_channel: 'telegram' | 'email' | 'both';
}
