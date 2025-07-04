// src/utils/axiosConfig.js
import axios from 'axios';

// Configuración base de Axios
const axiosInstance = axios.create({
    baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8080/api', // URL base de la API
    timeout: 10000, // 10 segundos
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor para requests
axiosInstance.interceptors.request.use(
    (config) => {
        // Agregar token de autenticación si existe
        const token = localStorage.getItem('authToken');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Log para debugging en desarrollo
        if (process.env.NODE_ENV === 'development') {
            console.log('Request:', config);
        }
        
        return config;
    },
    (error) => {
        console.error('Request error:', error);
        return Promise.reject(error);
    }
);

// Interceptor para responses
axiosInstance.interceptors.response.use(
    (response) => {
        // Log para debugging en desarrollo
        if (process.env.NODE_ENV === 'development') {
            console.log('Response:', response);
        }
        
        return response;
    },
    (error) => {
        // Manejo global de errores
        if (error.response) {
            // El servidor respondió con un código de estado fuera del rango 2xx
            console.error('Response error:', error.response.data);
            console.error('Status:', error.response.status);
            
            // Manejar errores específicos
            switch (error.response.status) {
                case 401:
                    // No autorizado - redirigir al login
                    localStorage.removeItem('authToken');
                    window.location.href = '/login';
                    break;
                case 403:
                    // Prohibido
                    console.error('Acceso prohibido');
                    break;
                case 404:
                    // No encontrado
                    console.error('Recurso no encontrado');
                    break;
                case 500:
                    // Error interno del servidor
                    console.error('Error interno del servidor');
                    break;
                default:
                    console.error('Error desconocido:', error.response.status);
            }
        } else if (error.request) {
            // La petición fue hecha pero no se recibió respuesta
            console.error('Network error:', error.request);
        } else {
            // Algo ocurrió al configurar la petición
            console.error('Config error:', error.message);
        }
        
        return Promise.reject(error);
    }
);

export default axiosInstance;

// Funciones de utilidad para las peticiones de contacto
export const contactanosAPI = {
    // Enviar mensaje de contacto
    enviarMensaje: (datos) => {
        return axiosInstance.post('/contactanos', datos);
    },
};

// Función para manejar errores de manera consistente
export const manejarError = (error) => {
    let mensaje = 'Error desconocido';
    
    if (error.response) {
        mensaje = error.response.data?.message || 
                 `Error del servidor (${error.response.status})`;
    } else if (error.request) {
        mensaje = 'No se pudo conectar con el servidor. Verifica tu conexión a internet.';
    } else {
        mensaje = error.message || 'Error inesperado';
    }
    
    return mensaje;
};