/**
 * Configuración de la API para el Dashboard Administrativo
 * Centro de Terapias Juan Pablo II
 */

export const API_CONFIG = {
  BASE_URL: 'http://localhost:8001',
  ENDPOINTS: {
    AUTH: {
      LOGIN: '/auth/login',
      ME: '/auth/me',
      LOGOUT: '/auth/logout'
    },
    ADMIN: {
      INQUIRIES: '/admin/inquiries',
      CONVERSATIONS: '/admin/conversations',
      MESSAGES: '/admin/messages',
      USERS: '/admin/users',
      STATS: '/admin/stats'
    }
  }
};

/**
 * Helper para obtener la URL completa de un endpoint
 */
export function getApiUrl(endpoint: string): string {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
}

export default API_CONFIG;
