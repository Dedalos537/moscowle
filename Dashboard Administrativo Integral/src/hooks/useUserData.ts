import { useState, useEffect } from 'react';

export interface UserData {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  specialty?: string;
  avatar?: string;
  phone?: string;
  lastLogin?: Date;
}

export function useUserData() {
  const [userData, setUserData] = useState<UserData>({
    id: 1,
    firstName: 'Administrador',
    lastName: 'Sistema',
    email: 'admin@terapias.com',
    role: 'admin',
    specialty: 'Administración General'
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Cargar datos del usuario
  const loadUserData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Primero intentar cargar desde localStorage
      const storedUserData = localStorage.getItem('user_data');
      if (storedUserData) {
        const parsedData = JSON.parse(storedUserData);
        setUserData({
          id: parsedData.id || 1,
          firstName: parsedData.first_name || 'Administrador',
          lastName: parsedData.last_name || 'Sistema',
          email: parsedData.email || 'admin@terapias.com',
          role: parsedData.role || 'admin',
          specialty: parsedData.specialty || 'Administración General',
          phone: parsedData.phone,
          avatar: parsedData.avatar
        });
      }

      // En un escenario real, también se haría una llamada a la API:
      // const token = localStorage.getItem('auth_token');
      // const response = await fetch('http://localhost:8000/auth/me', {
      //   headers: {
      //     'Authorization': `Bearer ${token}`,
      //     'Content-Type': 'application/json'
      //   }
      // });
      // const apiData = await response.json();
      // setUserData(apiData);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar datos del usuario');
    } finally {
      setIsLoading(false);
    }
  };

  // Actualizar datos del usuario
  const updateUserData = async (updates: Partial<UserData>) => {
    try {
      setUserData(prev => ({ ...prev, ...updates }));
      
      // En un escenario real, se enviarían los datos a la API:
      // const token = localStorage.getItem('auth_token');
      // await fetch('http://localhost:8000/auth/profile', {
      //   method: 'PATCH',
      //   headers: {
      //     'Authorization': `Bearer ${token}`,
      //     'Content-Type': 'application/json'
      //   },
      //   body: JSON.stringify(updates)
      // });

      // Actualizar localStorage
      const currentData = localStorage.getItem('user_data');
      if (currentData) {
        const parsedData = JSON.parse(currentData);
        localStorage.setItem('user_data', JSON.stringify({ ...parsedData, ...updates }));
      }
    } catch (err) {
      setError('Error al actualizar datos del usuario');
    }
  };

  // Obtener rol formateado
  const getFormattedRole = () => {
    switch (userData.role) {
      case 'admin': return 'Administrador';
      case 'therapist': return 'Terapeuta';
      case 'assistant': return 'Asistente';
      default: return userData.role;
    }
  };

  // Obtener iniciales
  const getInitials = () => {
    return `${userData.firstName[0]}${userData.lastName[0]}`;
  };

  // Obtener nombre completo
  const getFullName = () => {
    return `${userData.firstName} ${userData.lastName}`;
  };

  // Cargar datos al montar
  useEffect(() => {
    loadUserData();
  }, []);

  return {
    userData,
    isLoading,
    error,
    loadUserData,
    updateUserData,
    getFormattedRole,
    getInitials,
    getFullName
  };
}