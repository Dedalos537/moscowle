import { useState, useEffect, useCallback } from 'react';

export interface Notification {
  id: number;
  type: 'message' | 'alert' | 'incident' | 'system';
  title: string;
  text: string;
  time: string;
  read: boolean;
  priority: 'low' | 'medium' | 'high';
  createdAt?: Date;
}

const API_BASE_URL = 'http://localhost:8000';

export function useNotifications() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar notificaciones desde la API
  const loadNotifications = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const token = localStorage.getItem('auth_token');
      
      // En un escenario real, esto sería una llamada a la API
      // const response = await fetch(`${API_BASE_URL}/admin/notifications`, {
      //   headers: {
      //     'Authorization': `Bearer ${token}`,
      //     'Content-Type': 'application/json'
      //   }
      // });
      
      // Por ahora simulamos datos
      const simulatedNotifications: Notification[] = [
        { 
          id: Date.now() + 1, 
          type: 'message', 
          title: 'Nueva consulta web',
          text: 'Nueva consulta recibida desde la página web sobre terapia de lenguaje', 
          time: 'Ahora', 
          read: false,
          priority: 'high',
          createdAt: new Date()
        },
        { 
          id: Date.now() + 2, 
          type: 'alert', 
          title: 'Pago pendiente',
          text: 'Pago pendiente de procesar - Factura #2024-002', 
          time: '10 min', 
          read: false,
          priority: 'medium',
          createdAt: new Date(Date.now() - 10 * 60 * 1000)
        },
        { 
          id: Date.now() + 3, 
          type: 'system', 
          title: 'Backup completado',
          text: 'Respaldo automático de base de datos completado exitosamente', 
          time: '1 hr', 
          read: true,
          priority: 'low',
          createdAt: new Date(Date.now() - 60 * 60 * 1000)
        },
      ];
      
      setNotifications(simulatedNotifications);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar notificaciones');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Marcar notificación como leída
  const markAsRead = useCallback(async (notificationId: number) => {
    try {
      // En un escenario real:
      // await fetch(`${API_BASE_URL}/admin/notifications/${notificationId}/mark-read`, {
      //   method: 'PATCH',
      //   headers: { 'Authorization': `Bearer ${token}` }
      // });
      
      setNotifications(prev => 
        prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
      );
    } catch (err) {
      setError('Error al marcar notificación como leída');
    }
  }, []);

  // Marcar todas como leídas
  const markAllAsRead = useCallback(async () => {
    try {
      // En un escenario real:
      // await fetch(`${API_BASE_URL}/admin/notifications/mark-all-read`, {
      //   method: 'PATCH',
      //   headers: { 'Authorization': `Bearer ${token}` }
      // });
      
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch (err) {
      setError('Error al marcar todas las notificaciones como leídas');
    }
  }, []);

  // Eliminar notificación
  const removeNotification = useCallback(async (notificationId: number) => {
    try {
      // En un escenario real:
      // await fetch(`${API_BASE_URL}/admin/notifications/${notificationId}`, {
      //   method: 'DELETE',
      //   headers: { 'Authorization': `Bearer ${token}` }
      // });
      
      setNotifications(prev => prev.filter(n => n.id !== notificationId));
    } catch (err) {
      setError('Error al eliminar notificación');
    }
  }, []);

  // Agregar nueva notificación (para notificaciones en tiempo real)
  const addNotification = useCallback((notification: Omit<Notification, 'id'>) => {
    const newNotification: Notification = {
      ...notification,
      id: Date.now(),
      createdAt: new Date()
    };
    
    setNotifications(prev => [newNotification, ...prev]);
  }, []);

  // Obtener notificaciones no leídas
  const unreadNotifications = notifications.filter(n => !n.read);

  // Cargar notificaciones al montar el componente
  useEffect(() => {
    loadNotifications();
    
    // Actualizar cada 30 segundos
    const interval = setInterval(loadNotifications, 30000);
    
    return () => clearInterval(interval);
  }, [loadNotifications]);

  return {
    notifications,
    unreadNotifications,
    isLoading,
    error,
    loadNotifications,
    markAsRead,
    markAllAsRead,
    removeNotification,
    addNotification
  };
}