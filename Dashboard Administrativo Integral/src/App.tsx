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
import { LoginForm } from './components/auth/LoginForm';
import { Toaster } from './components/ui/sonner';

export default function App() {
  const [activeModule, setActiveModule] = useState('dashboard');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Check authentication status on app load
  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  // Apply dark mode class to HTML element
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const handleLogin = (token: string) => {
    setIsAuthenticated(true);
  };

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

  // Show login form if not authenticated
  if (!isAuthenticated) {
    return <LoginForm onLogin={handleLogin} />;
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