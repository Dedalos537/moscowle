import { useState } from 'react';
import { Calendar, Clock, Plus, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Avatar, AvatarFallback } from '../ui/avatar';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';

const therapyTypes = {
  language: { name: 'Lenguaje', color: '#4CAF50' },
  occupational: { name: 'Ocupacional', color: '#8BC34A' },
  physical: { name: 'Física', color: '#2E7D32' },
  psychological: { name: 'Psicológica', color: '#A5D6A7' },
};

const sessions = [
  { 
    id: 1, 
    time: '08:00 - 09:00', 
    patient: 'Carlos González', 
    therapist: 'Dra. Ana Pérez',
    type: 'language',
    room: 'Sala 1',
    status: 'confirmed'
  },
  { 
    id: 2, 
    time: '09:00 - 10:00', 
    patient: 'María Rodríguez', 
    therapist: 'Lic. Roberto Díaz',
    type: 'occupational',
    room: 'Sala 2',
    status: 'confirmed'
  },
  { 
    id: 3, 
    time: '10:00 - 11:00', 
    patient: 'Luis Martínez', 
    therapist: 'Dr. Juan López',
    type: 'physical',
    room: 'Sala 3',
    status: 'pending'
  },
  { 
    id: 4, 
    time: '11:00 - 12:00', 
    patient: 'Ana Sánchez', 
    therapist: 'Dra. Laura Méndez',
    type: 'psychological',
    room: 'Sala 4',
    status: 'confirmed'
  },
  { 
    id: 5, 
    time: '12:00 - 13:00', 
    patient: 'Pedro Gómez', 
    therapist: 'Dra. Ana Pérez',
    type: 'language',
    room: 'Sala 1',
    status: 'cancelled'
  },
];

const weekDays = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];

export function ScheduleModule() {
  const [selectedDay, setSelectedDay] = useState(2); // Wednesday
  const [viewMode, setViewMode] = useState('week');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Control de Horarios y Asistencia</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Gestiona sesiones, terapias y registro de asistencia
          </p>
        </div>
        <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
          <Plus className="w-4 h-4 mr-2" />
          Nueva Sesión
        </Button>
      </div>

      {/* Calendar Controls */}
      <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button variant="outline" size="icon">
                <ChevronLeft className="w-4 h-4" />
              </Button>
              <div className="text-center">
                <h3 className="text-gray-900 dark:text-white">Octubre 2025</h3>
                <p className="text-sm text-gray-500">Semana 27 - 02 Nov</p>
              </div>
              <Button variant="outline" size="icon">
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="flex items-center gap-3">
              <Select value={viewMode} onValueChange={setViewMode}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="day">Día</SelectItem>
                  <SelectItem value="week">Semana</SelectItem>
                  <SelectItem value="month">Mes</SelectItem>
                </SelectContent>
              </Select>
              
              <Button variant="outline">
                <Filter className="w-4 h-4 mr-2" />
                Filtrar
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Week View */}
      <div className="grid grid-cols-1 lg:grid-cols-6 gap-4">
        {weekDays.map((day, index) => (
          <Card 
            key={day}
            className={`border-gray-200 dark:border-gray-800 cursor-pointer transition-all ${
              selectedDay === index 
                ? 'bg-gradient-to-br from-[#E8F5E9] to-white dark:from-[#2E7D32]/20 dark:to-[#1E1E2E] ring-2 ring-[#4CAF50]' 
                : 'bg-white dark:bg-[#1E1E2E] hover:shadow-lg'
            }`}
            onClick={() => setSelectedDay(index)}
          >
            <CardContent className="p-4">
              <div className="text-center mb-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">{day}</p>
                <h3 className="text-gray-900 dark:text-white mt-1">{28 + index}</h3>
              </div>
              <div className="space-y-2">
                <Badge className="w-full bg-[#4CAF50]/10 text-[#4CAF50] border-[#4CAF50]/20">
                  6 sesiones
                </Badge>
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-[#4CAF50]" />
                  <div className="w-2 h-2 rounded-full bg-[#8BC34A]" />
                  <div className="w-2 h-2 rounded-full bg-[#2E7D32]" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Daily Schedule */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Schedule Timeline */}
        <Card className="lg:col-span-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">
              Agenda - {weekDays[selectedDay]} 30
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {sessions.map((session) => {
                const therapy = therapyTypes[session.type as keyof typeof therapyTypes];
                return (
                  <div 
                    key={session.id}
                    className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all"
                    style={{
                      borderLeftWidth: '4px',
                      borderLeftColor: therapy.color
                    }}
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className="text-center">
                        <Clock className="w-5 h-5 text-gray-400 mb-1" />
                        <p className="text-xs text-gray-600 dark:text-gray-400 whitespace-nowrap">
                          {session.time}
                        </p>
                      </div>
                      
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="text-sm text-gray-900 dark:text-white">{session.patient}</h4>
                          <Badge 
                            style={{ 
                              backgroundColor: `${therapy.color}20`,
                              color: therapy.color,
                              borderColor: `${therapy.color}40`
                            }}
                          >
                            {therapy.name}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {session.therapist} • {session.room}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      {session.status === 'confirmed' && (
                        <Badge className="bg-green-100 text-green-700 border-green-200">
                          Confirmada
                        </Badge>
                      )}
                      {session.status === 'pending' && (
                        <Badge className="bg-yellow-100 text-yellow-700 border-yellow-200">
                          Pendiente
                        </Badge>
                      )}
                      {session.status === 'cancelled' && (
                        <Badge className="bg-red-100 text-red-700 border-red-200">
                          Cancelada
                        </Badge>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Therapists Availability */}
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Terapeutas Disponibles</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                { name: 'Dra. Ana Pérez', sessions: 4, available: true },
                { name: 'Lic. Roberto Díaz', sessions: 3, available: true },
                { name: 'Dr. Juan López', sessions: 5, available: false },
                { name: 'Dra. Laura Méndez', sessions: 2, available: true },
              ].map((therapist, index) => (
                <div key={index} className="flex items-center gap-3">
                  <Avatar>
                    <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                      {therapist.name.split(' ')[1][0]}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900 dark:text-white">{therapist.name}</p>
                    <p className="text-xs text-gray-500">{therapist.sessions} sesiones hoy</p>
                  </div>
                  <div className={`w-2 h-2 rounded-full ${therapist.available ? 'bg-green-500' : 'bg-red-500'}`} />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Sesiones Hoy</p>
            <h3 className="text-gray-900 dark:text-white">24</h3>
          </CardContent>
        </Card>
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Asistencia</p>
            <h3 className="text-gray-900 dark:text-white">92%</h3>
          </CardContent>
        </Card>
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Cancelaciones</p>
            <h3 className="text-gray-900 dark:text-white">2</h3>
          </CardContent>
        </Card>
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-4">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">Pendientes</p>
            <h3 className="text-gray-900 dark:text-white">3</h3>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
