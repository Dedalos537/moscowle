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
import { NPSSurvey } from './components/dashboard/NPSSurvey';
import { Toaster } from './components/ui/sonner';
import { getBackendUrl } from './utils/urlResolver';

export default function App() {
  const [activeModule, setActiveModule] = useState('dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [showNPSSurvey, setShowNPSSurvey] = useState(false);
  const env: any = (import.meta as any)?.env || {};
  const BACKEND = getBackendUrl((env.VITE_BACKEND_URL as string));
  const PRINCIPAL = (env.VITE_PRINCIPAL_URL as string) || 'http://localhost:3002';

  // Check authentication status on app load
  useEffect(() => {
    const checkAuth = async () => {
      console.log('[Dashboard] Starting auth check...');
      
      // Primero intenta leer de los parámetros de URL (pasados desde Principal_Page)
      const params = new URLSearchParams(window.location.search);
      const tokenFromUrl = params.get('token');
      const userFromUrl = params.get('user');
      
      console.log('[Dashboard] URL parameters:', { 
        tokenFromUrl: tokenFromUrl ? tokenFromUrl.substring(0, 50) + '...' : null,
        userFromUrl: userFromUrl ? userFromUrl.substring(0, 50) + '...' : null
      });
      
      // Si vinieron en URL, guardar en localStorage
      if (tokenFromUrl && userFromUrl) {
        console.log('[Dashboard] Found token in URL, saving to localStorage');
        localStorage.setItem('auth_token', tokenFromUrl);
        localStorage.setItem('user_data', userFromUrl);
      }
      
      // Ahora revisar localStorage
      const token = localStorage.getItem('auth_token');
      const userData = localStorage.getItem('user_data');
      
      console.log('[Dashboard] Auth check result:', {
        hasToken: !!token,
        hasUserData: !!userData,
        tokenValue: token ? token.substring(0, 50) + '...' : null,
        userDataValue: userData,
        principalUrl: PRINCIPAL,
      });
      
      if (!token || !userData) {
        console.warn('[Dashboard] ❌ No token or user data found. Redirecting to:', PRINCIPAL);
        setIsLoading(false);
        setTimeout(() => {
          window.location.href = PRINCIPAL;
        }, 100);
        return;
      }

      console.log('[Dashboard] ✅ Auth check passed. Setting authenticated = true');
      // User has token and user_data - allow access
      setIsAuthenticated(true);
      setIsLoading(false);
    };

    checkAuth();
  }, [PRINCIPAL]);

  // Apply dark mode class to HTML element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  // Show NPS survey after user is authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const timer = setTimeout(() => {
        // Check if user has already completed survey today
        const lastSurveyDate = localStorage.getItem('nps_survey_date');
        const today = new Date().toISOString().split('T')[0];
        
        if (!lastSurveyDate || lastSurveyDate !== today) {
          setShowNPSSurvey(true);
        }
      }, 3000); // Show after 3 seconds
      
      return () => clearTimeout(timer);
    }
  }, [isAuthenticated]);

  const handleLogout = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    setIsAuthenticated(false);
    setActiveModule('dashboard');
  };

  const handleNPSSubmit = async (score: number, feedback: string) => {
    try {
      console.log('[Dashboard] NPS Survey submitted:', { score, feedback });
      
      // Mark survey as completed for today
      const today = new Date().toISOString().split('T')[0];
      localStorage.setItem('nps_survey_date', today);
      
      // TODO: Send NPS data to backend if needed
      // const response = await fetch(`${BACKEND}/api/nps`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //     'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
      //   },
      //   body: JSON.stringify({ score, feedback })
      // });
      
      setShowNPSSurvey(false);
    } catch (error) {
      console.error('[Dashboard] Error submitting NPS:', error);
    }
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
      
      {/* NPS Survey Modal */}
      <NPSSurvey 
        isOpen={showNPSSurvey}
        onClose={() => setShowNPSSurvey(false)}
        onSubmit={handleNPSSubmit}
      />
    </div>
  );
}