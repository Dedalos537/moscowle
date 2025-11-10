// API Configuration
export const API_CONFIG = {
  // URL base del backend - Hardcoded para producción Docker
  BASE_URL: 'http://localhost:8001',
  
  // Endpoints públicos
  PUBLIC: {
    CONTACT: '/public/contact',
    MESSAGE: '/public/message',
  },
  
  // Endpoints de autenticación
  AUTH: {
    LOGIN: '/auth/login',
    ME: '/auth/me',
  },
  
  // Endpoints administrativos
  ADMIN: {
    INQUIRIES: '/admin/inquiries',
    CONVERSATIONS: '/admin/conversations',
    MESSAGES: '/admin/messages',
    STATS: '/admin/stats',
  },
  
  // Endpoints de salud
  HEALTH: '/health',
};

// Helper para construir URLs completas
export const getApiUrl = (endpoint: string): string => {
  return `${API_CONFIG.BASE_URL}${endpoint}`;
};
