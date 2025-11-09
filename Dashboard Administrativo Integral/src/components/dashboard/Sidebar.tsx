import { useState } from 'react';
import { 
  LayoutDashboard, 
  MessageSquare, 
  Calendar, 
  DollarSign, 
  Package, 
  ClipboardCheck, 
  FileText, 
  Users, 
  AlertCircle, 
  Gamepad2,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { cn } from '../ui/utils';
import { Badge } from '../ui/badge';

interface SidebarProps {
  activeModule: string;
  onModuleChange: (module: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

const menuItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard, badge: null },
  { id: 'messages', label: 'Mensajería', icon: MessageSquare, badge: 12 },
  { id: 'schedule', label: 'Horarios', icon: Calendar, badge: null },
  { id: 'finance', label: 'Finanzas', icon: DollarSign, badge: 3 },
  { id: 'inventory', label: 'Inventario', icon: Package, badge: 5 },
  { id: 'attendance', label: 'Asistencia', icon: ClipboardCheck, badge: null },
  { id: 'reports', label: 'Informes', icon: FileText, badge: null },
  { id: 'users', label: 'Usuarios', icon: Users, badge: null },
  { id: 'itil', label: 'Mejora Continua', icon: AlertCircle, badge: 8 },
  { id: 'games', label: 'Juegos LMS', icon: Gamepad2, badge: 'Nuevo' },
];

export function Sidebar({ activeModule, onModuleChange, isCollapsed, onToggleCollapse }: SidebarProps) {
  return (
    <div 
      className={cn(
        "h-screen bg-white dark:bg-[#1E1E2E] border-r border-gray-200 dark:border-gray-800 transition-all duration-300 flex flex-col",
        isCollapsed ? "w-20" : "w-64"
      )}
    >
      {/* Logo Header */}
      <div className="h-16 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between px-4">
        {!isCollapsed && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] flex items-center justify-center text-white">
              <span>JP</span>
            </div>
            <div>
              <h2 className="text-[#3E3A54] dark:text-white">Juan Pablo II</h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">Centro de Terapias</p>
            </div>
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        >
          {isCollapsed ? (
            <ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          ) : (
            <ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" />
          )}
        </button>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 overflow-y-auto py-4 px-2">
        <div className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeModule === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => onModuleChange(item.id)}
                className={cn(
                  "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200",
                  isActive 
                    ? "bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white shadow-lg shadow-green-500/30" 
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800",
                  isCollapsed && "justify-center"
                )}
              >
                <Icon className={cn("w-5 h-5 flex-shrink-0", isActive && "animate-pulse")} />
                {!isCollapsed && (
                  <>
                    <span className="flex-1 text-left">{item.label}</span>
                    {item.badge && (
                      <Badge 
                        variant={isActive ? "secondary" : "default"}
                        className={cn(
                          "text-xs",
                          isActive 
                            ? "bg-white/20 text-white border-white/30" 
                            : "bg-[#4CAF50] text-white"
                        )}
                      >
                        {item.badge}
                      </Badge>
                    )}
                  </>
                )}
              </button>
            );
          })}
        </div>
      </nav>

      {/* Footer Info */}
      {!isCollapsed && (
        <div className="p-4 border-t border-gray-200 dark:border-gray-800">
          <div className="bg-gradient-to-br from-[#E8F5E9] to-[#A5D6A7] dark:from-[#2E7D32]/20 dark:to-[#4CAF50]/10 rounded-lg p-3">
            <p className="text-xs text-[#2E7D32] dark:text-[#A5D6A7]">
              Sistema de Gestión v2.0
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
              Actualizado: Oct 2025
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
