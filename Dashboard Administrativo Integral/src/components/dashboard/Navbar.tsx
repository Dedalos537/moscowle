import { useState } from 'react';
import { Search, Bell, Moon, Sun, Settings, LogOut, User, MessageSquare, AlertTriangle, Clock, CheckCircle, X } from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { Badge } from '../ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { useNotifications } from '../../hooks/useNotifications';
import { useUserData } from '../../hooks/useUserData';
import { UserProfile } from './UserProfile';
import '../../styles/navbar.css';

interface NavbarProps {
  isDarkMode: boolean;
  onToggleDarkMode: () => void;
  onLogout?: () => void;
}

export function Navbar({ isDarkMode, onToggleDarkMode, onLogout }: NavbarProps) {
  // Usar hooks personalizados
  const { 
    notifications, 
    unreadNotifications, 
    markAsRead, 
    markAllAsRead, 
    removeNotification 
  } = useNotifications();
  
  const { 
    userData, 
    getFormattedRole, 
    getInitials, 
    getFullName 
  } = useUserData();

  const [showUserProfile, setShowUserProfile] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showUserEdit, setShowUserEdit] = useState(false);

  const handleLogout = () => {
    // Limpiar localStorage
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    
    // Llamar al callback de logout si existe
    if (onLogout) {
      onLogout();
    }
    
    // Redirigir a la página principal
    window.location.href = 'http://localhost:3002';
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'message': return <MessageSquare className="w-4 h-4" />;
      case 'alert': return <AlertTriangle className="w-4 h-4" />;
      case 'incident': return <Settings className="w-4 h-4" />;
      case 'system': return <CheckCircle className="w-4 h-4" />;
      default: return <Bell className="w-4 h-4" />;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'high': return 'priority-high';
      case 'medium': return 'priority-medium';
      case 'low': return 'priority-low';
      default: return 'text-gray-600';
    }
  };

  return (
    <div className="h-16 bg-white dark:bg-[#1E1E2E] border-b border-gray-200 dark:border-gray-800 px-6 flex items-center justify-between dark-mode-transition">
      {/* Search Bar */}
      <div className="flex-1 max-w-xl navbar-search">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input 
            placeholder="Buscar pacientes, terapeutas, reportes..." 
            className="pl-10 bg-gray-50 dark:bg-gray-900 border-gray-200 dark:border-gray-700 dark-mode-transition"
          />
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 ml-6">
        {/* Dark Mode Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleDarkMode}
          className="rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 dark-mode-transition navbar-button button-hover-effect"
        >
          {isDarkMode ? (
            <Sun className="w-5 h-5 text-[#4CAF50]" />
          ) : (
            <Moon className="w-5 h-5 text-gray-600" />
          )}
        </Button>

        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="relative rounded-full navbar-button">
              <Bell className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              {unreadNotifications.length > 0 && (
                <Badge className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center p-0 bg-[#4CAF50] text-white text-xs notification-badge">
                  {unreadNotifications.length}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-96 glass-dropdown">
            <div className="flex items-center justify-between p-4">
              <DropdownMenuLabel className="p-0">Notificaciones</DropdownMenuLabel>
              <div className="flex items-center gap-2">
                {unreadNotifications.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={markAllAsRead}
                    className="text-xs text-[#4CAF50] hover:text-[#4CAF50] button-hover-effect"
                  >
                    Marcar todas como leídas
                  </Button>
                )}
              </div>
            </div>
            <Separator />
            <ScrollArea className="max-h-80">
              {notifications.length === 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <Bell className="w-8 h-8 mx-auto mb-2 text-gray-300" />
                  <p className="text-sm">No hay notificaciones</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className={`notification-item p-3 hover:bg-gray-50 dark:hover:bg-gray-800 dark-mode-transition cursor-pointer ${
                        !notif.read ? 'notification-unread unread' : ''
                      }`}
                      onClick={() => markAsRead(notif.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`mt-1 ${getPriorityColor(notif.priority)}`}>
                          {getNotificationIcon(notif.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <p className={`text-sm font-medium ${!notif.read ? 'text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>
                              {notif.title}
                            </p>
                            <div className="flex items-center gap-1">
                              <span className="text-xs text-gray-500 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {notif.time}
                              </span>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={(e: React.MouseEvent) => {
                                  e.stopPropagation();
                                  removeNotification(notif.id);
                                }}
                                className="w-6 h-6 p-0 hover:bg-red-100 hover:text-red-600 dark-mode-transition"
                              >
                                <X className="w-3 h-3" />
                              </Button>
                            </div>
                          </div>
                          <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
                            {notif.text}
                          </p>
                          {!notif.read && (
                            <div className="w-2 h-2 bg-[#4CAF50] rounded-full mt-2 unread-indicator"></div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </ScrollArea>
            <Separator />
            <div className="p-2">
              <Button 
                variant="ghost" 
                className="w-full text-[#4CAF50] hover:text-[#4CAF50] hover:bg-[#4CAF50]/10 button-hover-effect"
              >
                Ver todas las notificaciones
              </Button>
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Settings */}
        <Dialog open={showSettings} onOpenChange={setShowSettings}>
          <DialogTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full">
              <Settings className="w-5 h-5 text-gray-600 dark:text-gray-300" />
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Configuración</DialogTitle>
              <DialogDescription>
                Ajusta la configuración de la aplicación
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Modo oscuro</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onToggleDarkMode}
                  className="gap-2"
                >
                  {isDarkMode ? (
                    <>
                      <Sun className="w-4 h-4" />
                      Claro
                    </>
                  ) : (
                    <>
                      <Moon className="w-4 h-4" />
                      Oscuro
                    </>
                  )}
                </Button>
              </div>
              <Separator />
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Notificaciones</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Nuevos mensajes</span>
                    <input type="checkbox" defaultChecked className="rounded" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Alertas del sistema</span>
                    <input type="checkbox" defaultChecked className="rounded" />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Recordatorios de citas</span>
                    <input type="checkbox" defaultChecked className="rounded" />
                  </div>
                </div>
              </div>
              <Separator />
              <div className="space-y-3">
                <h4 className="text-sm font-medium">Preferencias</h4>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Idioma</span>
                    <select className="text-sm border rounded px-2 py-1">
                      <option>Español</option>
                      <option>English</option>
                    </select>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Zona horaria</span>
                    <select className="text-sm border rounded px-2 py-1">
                      <option>GMT-6 (México)</option>
                      <option>GMT-5 (Colombia)</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>

        {/* User Profile */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="gap-2 hover:bg-gray-100 dark:hover:bg-gray-800 dark-mode-transition navbar-button">
              <Avatar className="w-8 h-8 user-avatar">
                <AvatarImage src={userData.avatar} alt={getFullName()} />
                <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                  {getInitials()}
                </AvatarFallback>
              </Avatar>
              <div className="hidden md:block text-left navbar-user-info">
                <p className="text-sm text-gray-700 dark:text-gray-200">
                  {getFullName()}
                </p>
                <p className="text-xs text-gray-500">
                  {getFormattedRole()}
                </p>
              </div>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64 glass-dropdown">
            <div className="p-4 border-b">
              <div className="flex items-center gap-3">
                <Avatar className="w-12 h-12 user-avatar">
                  <AvatarImage src={userData.avatar} alt={getFullName()} />
                  <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white text-lg">
                    {getInitials()}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-sm font-medium text-gray-900 dark:text-white">
                    {getFullName()}
                  </p>
                  <p className="text-xs text-gray-500">{userData.email}</p>
                  {userData.specialty && (
                    <p className="text-xs text-[#4CAF50]">{userData.specialty}</p>
                  )}
                </div>
              </div>
            </div>
            <DropdownMenuLabel>Mi Cuenta</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setShowUserProfile(true)} className="button-hover-effect">
              <User className="w-4 h-4 mr-2" />
              Ver Perfil
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setShowUserEdit(true)} className="button-hover-effect">
              <User className="w-4 h-4 mr-2" />
              Editar Perfil
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setShowSettings(true)} className="button-hover-effect">
              <Settings className="w-4 h-4 mr-2" />
              Configuración
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem 
              className="text-red-600 button-hover-effect"
              onClick={handleLogout}
            >
              <LogOut className="w-4 h-4 mr-2" />
              Cerrar Sesión
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* User Profile Dialog */}
      <Dialog open={showUserProfile} onOpenChange={setShowUserProfile}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Perfil de Usuario</DialogTitle>
            <DialogDescription>
              Información de tu cuenta y configuración personal
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            {/* Avatar y información básica */}
            <div className="flex items-center gap-4">
              <Avatar className="w-20 h-20">
                <AvatarImage src={userData.avatar} alt={getFullName()} />
                <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white text-2xl">
                  {getInitials()}
                </AvatarFallback>
              </Avatar>
              <div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  {getFullName()}
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400">{userData.email}</p>
                <Badge className="mt-1 bg-[#4CAF50] text-white">
                  {getFormattedRole()}
                </Badge>
              </div>
            </div>

            <Separator />

            {/* Información del perfil */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Nombre
                </label>
                <p className="text-sm text-gray-900 dark:text-white mt-1">
                  {userData.firstName}
                </p>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Apellido
                </label>
                <p className="text-sm text-gray-900 dark:text-white mt-1">
                  {userData.lastName}
                </p>
              </div>
              <div className="col-span-2">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Email
                </label>
                <p className="text-sm text-gray-900 dark:text-white mt-1">
                  {userData.email}
                </p>
              </div>
              {userData.specialty && (
                <div className="col-span-2">
                  <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Especialidad
                  </label>
                  <p className="text-sm text-gray-900 dark:text-white mt-1">
                    {userData.specialty}
                  </p>
                </div>
              )}
            </div>

            <Separator />

            {/* Estadísticas básicas */}
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">Último acceso</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">Hoy</p>
              </div>
              <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <p className="text-sm text-gray-600 dark:text-gray-400">Rol</p>
                <p className="text-sm font-medium text-gray-900 dark:text-white">
                  {getFormattedRole()}
                </p>
              </div>
            </div>

            {/* Botones de acción */}
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1">
                Editar Perfil
              </Button>
              <Button variant="outline" className="flex-1">
                Cambiar Contraseña
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* User Edit Profile Modal */}
      <Dialog open={showUserEdit} onOpenChange={setShowUserEdit}>
        <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
          <UserProfile onClose={() => setShowUserEdit(false)} />
        </DialogContent>
      </Dialog>
    </div>
  );
}
