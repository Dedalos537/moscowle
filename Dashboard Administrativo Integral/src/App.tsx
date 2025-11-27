import { useState, useEffect } from 'react';
import { Sidebar } from './components/dashboard/Sidebar';
import { Navbar } from './components/dashboard/Navbar';
import { DashboardHome } from './components/dashboard/DashboardHome';
import { MessagesModule } from './components/dashboard/MessagesModule';
import { ScheduleModule } from './components/dashboard/ScheduleModule';
import { FinanceModule } from './components/dashboard/FinanceModule';
import { ITILModule } from './components/dashboard/ITILModule';
import { GamesModule } from './components/dashboard/GamesModule';
import { AttendanceModule } from './components/dashboard/AttendanceModule';
import { ReportsModule } from './components/dashboard/ReportsModule';
import { UsersModule } from './components/dashboard/UsersModule';
import { InventoryModule } from './components/dashboard/InventoryModule';
import { Toaster } from './components/ui/sonner';

export default function App() {
  const [activeModule, setActiveModule] = useState('dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const env: any = (import.meta as any)?.env || {};
  const BACKEND = (env.VITE_BACKEND_URL as string) || 'http://127.0.0.1:8002';
  const PRINCIPAL = (env.VITE_PRINCIPAL_URL as string) || 'http://localhost:3002';

  // Check authentication status on app load
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token');
      const ALLOW_BYPASS = env.VITE_BYPASS_AUTH === 'true' || env.DEV === true;
      if (!token) {
        setIsLoading(false);
        // Redirect to main site if no token
        window.location.href = PRINCIPAL;
        return;
      }

      // Development/demo bypass: accept a special BYPASS token and skip server validation
      if (token === 'BYPASS' && ALLOW_BYPASS) {
        try {
          const stored = localStorage.getItem('user_data');
          if (stored) {
            // keep provided user_data
            setIsAuthenticated(true);
          } else {
            // set a minimal user_data object so app can render
            localStorage.setItem('user_data', JSON.stringify({ id: 1, email: 'admin@local', is_admin: true }));
            setIsAuthenticated(true);
          }
        } finally {
          setIsLoading(false);
        }
        return;
      }

      try {
        // Debug: log token and target URL used for /api/auth/me
        // eslint-disable-next-line no-console
        console.debug('[Dashboard] token:', token, 'BACKEND:', BACKEND);
        const meUrl = `${BACKEND.replace(/\/$/, '')}/api/auth/me`;
        // eslint-disable-next-line no-console
        console.debug('[Dashboard] fetching', meUrl);
        const res = await fetch(`${BACKEND.replace(/\/$/, '')}/api/auth/me`, {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        });
        // eslint-disable-next-line no-console
        console.debug('[Dashboard] /api/auth/me status:', res.status);

        if (!res.ok) {
          // Invalid token or not authorized
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_data');
          setIsLoading(false);
          window.location.href = PRINCIPAL;
          return;
        }

        const user = await res.json();
        // Only allow access to users with admin role (adjust role name if different)
        if (user && (user.role === 'admin' || user.email === 'admin@juanpablo2.com')) {
          // persist/update local storage user data
          localStorage.setItem('user_data', JSON.stringify(user));
          setIsAuthenticated(true);
        } else {
          // Not an admin; redirect back to main site
          localStorage.removeItem('auth_token');
          localStorage.removeItem('user_data');
          setIsAuthenticated(false);
          setIsLoading(false);
          window.location.href = PRINCIPAL;
          return;
        }
      } catch (error) {
        console.error('Auth validation error:', error);
        localStorage.removeItem('auth_token');
        localStorage.removeItem('user_data');
        window.location.href = PRINCIPAL;
        return;
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  // Apply dark mode class to HTML element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    setIsAuthenticated(false);
    setActiveModule('dashboard');
  };

  const renderModule = () => {
    switch (activeModule) {
      case 'dashboard':
        return <DashboardHome />;
      case 'messages':
        return <MessagesModule />;
      case 'schedule':
        return <ScheduleModule />;
      case 'finance':
        return <FinanceModule />;
      case 'itil':
        return <ITILModule />;
      case 'games':
        return <GamesModule />;
      case 'attendance':
        return <AttendanceModule />;
      case 'reports':
        return <ReportsModule />;
      case 'users':
        return <UsersModule />;
      case 'inventory':
        return <InventoryModule />;
      default:
        return <DashboardHome />;
    }
  };

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#4CAF50] mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  // Show unauthorized access message if not authenticated
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#E8F5E9] to-[#C8E6C9] p-4">
        <div className="max-w-md w-full bg-white rounded-xl shadow-xl p-8 text-center">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] rounded-full flex items-center justify-center mb-6">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Acceso Restringido
          </h1>
          <p className="text-gray-600 mb-6">
            Debes iniciar sesión desde la página principal para acceder al dashboard administrativo.
          </p>
          <button 
            onClick={() => window.location.href = PRINCIPAL}
            className="w-full bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white py-3 px-4 rounded-lg hover:opacity-90 transition-opacity"
          >
            Ir a la Página Principal
          </button>
          <p className="text-sm text-gray-500 mt-4">
            Centro de Terapias Juan Pablo II
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#0f0f1a] overflow-hidden transition-colors duration-300">
      {/* Sidebar */}
      <Sidebar
        activeModule={activeModule}
        onModuleChange={setActiveModule}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Navbar */}
        <Navbar 
          isDarkMode={isDarkMode}
          onToggleDarkMode={() => setIsDarkMode(!isDarkMode)}
          onLogout={handleLogout}
        />

        {/* Content Area */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="max-w-7xl mx-auto">
            {renderModule()}
          </div>
        </main>
      </div>

      {/* Toast Notifications */}
      <Toaster />
    </div>
  );
}