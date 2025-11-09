import { useState } from 'react';
import { ClipboardCheck, Plus, Download, Calendar, CheckCircle, XCircle, Clock, TrendingUp, Search, Filter } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Avatar, AvatarFallback } from '../ui/avatar';
import { Progress } from '../ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';
import { Checkbox } from '../ui/checkbox';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Label } from '../ui/label';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';
import { toast } from 'sonner';

const attendanceData = [
  { 
    id: 1, 
    patient: 'Carlos González', 
    therapist: 'Dra. Ana Pérez',
    therapy: 'Lenguaje',
    date: '2025-10-30',
    time: '09:00 - 10:00',
    status: 'present',
    notes: 'Excelente participación'
  },
  { 
    id: 2, 
    patient: 'María Rodríguez', 
    therapist: 'Lic. Roberto Díaz',
    therapy: 'Ocupacional',
    date: '2025-10-30',
    time: '10:00 - 11:00',
    status: 'present',
    notes: ''
  },
  { 
    id: 3, 
    patient: 'Luis Martínez', 
    therapist: 'Dr. Juan López',
    therapy: 'Física',
    date: '2025-10-30',
    time: '11:00 - 12:00',
    status: 'absent',
    notes: 'Ausencia justificada'
  },
  { 
    id: 4, 
    patient: 'Ana Sánchez', 
    therapist: 'Dra. Laura Méndez',
    therapy: 'Psicológica',
    date: '2025-10-30',
    time: '12:00 - 13:00',
    status: 'late',
    notes: 'Llegó 15 min tarde'
  },
];

const weeklyTrend = [
  { day: 'Lun', rate: 92 },
  { day: 'Mar', rate: 88 },
  { day: 'Mié', rate: 95 },
  { day: 'Jue', rate: 91 },
  { day: 'Vie', rate: 87 },
];

const monthlyComparison = [
  { month: 'Jun', rate: 89 },
  { month: 'Jul', rate: 91 },
  { month: 'Ago', rate: 88 },
  { month: 'Sep', rate: 93 },
  { month: 'Oct', rate: 91 },
];

const statusConfig = {
  present: { label: 'Presente', color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
  absent: { label: 'Ausente', color: 'bg-red-100 text-red-700 border-red-200', icon: XCircle },
  late: { label: 'Tardanza', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: Clock },
  justified: { label: 'Justificado', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: CheckCircle },
};

export function AttendanceModule() {
  const [selectedDate, setSelectedDate] = useState('2025-10-30');
  const [filterTherapist, setFilterTherapist] = useState('all');
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [selectedRecords, setSelectedRecords] = useState<number[]>([]);

  const handleRegisterAttendance = () => {
    toast.success('Asistencia registrada correctamente');
    setIsRegisterOpen(false);
  };

  const handleExportData = () => {
    toast.success('Exportando datos de asistencia...');
  };

  const toggleRecordSelection = (id: number) => {
    setSelectedRecords(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Control de Asistencia</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Registro automático y manual de asistencia por sesión
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExportData}>
            <Download className="w-4 h-4 mr-2" />
            Exportar
          </Button>
          <Dialog open={isRegisterOpen} onOpenChange={setIsRegisterOpen}>
            <DialogTrigger asChild>
              <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
                <Plus className="w-4 h-4 mr-2" />
                Registrar Asistencia
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>Registrar Asistencia Manual</DialogTitle>
                <DialogDescription>
                  Complete los datos de la sesión y el estado de asistencia
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Paciente</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar paciente" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Carlos González</SelectItem>
                      <SelectItem value="2">María Rodríguez</SelectItem>
                      <SelectItem value="3">Luis Martínez</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Terapeuta</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar terapeuta" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">Dra. Ana Pérez</SelectItem>
                      <SelectItem value="2">Lic. Roberto Díaz</SelectItem>
                      <SelectItem value="3">Dr. Juan López</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Estado</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar estado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="present">Presente</SelectItem>
                      <SelectItem value="absent">Ausente</SelectItem>
                      <SelectItem value="late">Tardanza</SelectItem>
                      <SelectItem value="justified">Justificado</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Notas</Label>
                  <Input placeholder="Observaciones adicionales..." />
                </div>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setIsRegisterOpen(false)}>
                  Cancelar
                </Button>
                <Button 
                  className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white"
                  onClick={handleRegisterAttendance}
                >
                  Registrar
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Asistencia Hoy</p>
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">22/24</h3>
            <p className="text-xs text-green-600">91.7% de asistencia</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Promedio Semanal</p>
              <TrendingUp className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">90.6%</h3>
            <p className="text-xs text-gray-500">+2.3% vs semana anterior</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Ausencias del Mes</p>
              <XCircle className="w-5 h-5 text-red-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">18</h3>
            <p className="text-xs text-gray-500">3 justificadas</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Tardanzas</p>
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">5</h3>
            <Progress value={5} className="h-2 mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="daily" className="space-y-6">
        <TabsList className="bg-gray-100 dark:bg-gray-800">
          <TabsTrigger value="daily">Registro Diario</TabsTrigger>
          <TabsTrigger value="patient">Por Paciente</TabsTrigger>
          <TabsTrigger value="therapist">Por Terapeuta</TabsTrigger>
          <TabsTrigger value="analytics">Análisis</TabsTrigger>
        </TabsList>

        {/* Daily Tab */}
        <TabsContent value="daily" className="space-y-4">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-gray-900 dark:text-white">Registro del Día</CardTitle>
                <div className="flex items-center gap-3">
                  <Input 
                    type="date" 
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-auto"
                  />
                  <Select value={filterTherapist} onValueChange={setFilterTherapist}>
                    <SelectTrigger className="w-48">
                      <SelectValue placeholder="Todos los terapeutas" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Todos los terapeutas</SelectItem>
                      <SelectItem value="1">Dra. Ana Pérez</SelectItem>
                      <SelectItem value="2">Lic. Roberto Díaz</SelectItem>
                      <SelectItem value="3">Dr. Juan López</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox />
                    </TableHead>
                    <TableHead>Hora</TableHead>
                    <TableHead>Paciente</TableHead>
                    <TableHead>Terapeuta</TableHead>
                    <TableHead>Terapia</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Notas</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {attendanceData.map((record) => {
                    const status = statusConfig[record.status as keyof typeof statusConfig];
                    const StatusIcon = status.icon;
                    
                    return (
                      <TableRow key={record.id}>
                        <TableCell>
                          <Checkbox 
                            checked={selectedRecords.includes(record.id)}
                            onCheckedChange={() => toggleRecordSelection(record.id)}
                          />
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {record.time}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Avatar className="w-8 h-8">
                              <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white text-xs">
                                {record.patient.split(' ').map(n => n[0]).join('')}
                              </AvatarFallback>
                            </Avatar>
                            <span className="text-sm text-gray-900 dark:text-white">{record.patient}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {record.therapist}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{record.therapy}</Badge>
                        </TableCell>
                        <TableCell>
                          <Badge className={status.color}>
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {status.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400 max-w-xs truncate">
                          {record.notes || '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button variant="ghost" size="sm">
                            Editar
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Patient Tab */}
        <TabsContent value="patient" className="space-y-4">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-gray-900 dark:text-white">Asistencia por Paciente</CardTitle>
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input 
                      placeholder="Buscar paciente..." 
                      className="pl-10 w-64"
                    />
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {['Carlos González', 'María Rodríguez', 'Luis Martínez', 'Ana Sánchez'].map((patient, index) => {
                  const attendance = [95, 88, 92, 97][index];
                  return (
                    <div 
                      key={index}
                      className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 flex-1">
                          <Avatar className="w-12 h-12">
                            <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                              {patient.split(' ').map(n => n[0]).join('')}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex-1">
                            <h4 className="text-sm text-gray-900 dark:text-white mb-1">{patient}</h4>
                            <div className="flex items-center gap-4 text-xs text-gray-500">
                              <span>24 sesiones este mes</span>
                              <span>•</span>
                              <span className="text-green-600">{attendance}% asistencia</span>
                            </div>
                            <Progress value={attendance} className="h-2 mt-2 max-w-md" />
                          </div>
                        </div>
                        <Button variant="outline" size="sm">
                          Ver Detalle
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Therapist Tab */}
        <TabsContent value="therapist" className="space-y-4">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Asistencia por Terapeuta</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { name: 'Dra. Ana Pérez', sessions: 28, attendance: 94 },
                  { name: 'Lic. Roberto Díaz', sessions: 24, attendance: 89 },
                  { name: 'Dr. Juan López', sessions: 32, attendance: 91 },
                  { name: 'Dra. Laura Méndez', sessions: 20, attendance: 96 },
                ].map((therapist, index) => (
                  <div 
                    key={index}
                    className="p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Avatar className="w-10 h-10">
                          <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                            {therapist.name.split(' ')[1][0]}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <h4 className="text-sm text-gray-900 dark:text-white">{therapist.name}</h4>
                          <p className="text-xs text-gray-500">{therapist.sessions} sesiones programadas</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-gray-900 dark:text-white">{therapist.attendance}%</p>
                        <p className="text-xs text-gray-500">asistencia</p>
                      </div>
                    </div>
                    <Progress value={therapist.attendance} className="h-2" />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Weekly Trend */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Tendencia Semanal</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={weeklyTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="day" stroke="#666" />
                    <YAxis stroke="#666" domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px'
                      }} 
                    />
                    <Line 
                      type="monotone" 
                      dataKey="rate" 
                      stroke="#4CAF50" 
                      strokeWidth={3}
                      dot={{ fill: '#4CAF50', r: 5 }}
                      name="Asistencia %"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Monthly Comparison */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Comparación Mensual</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={monthlyComparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="month" stroke="#666" />
                    <YAxis stroke="#666" domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px'
                      }} 
                    />
                    <Bar dataKey="rate" fill="#4CAF50" radius={[8, 8, 0, 0]} name="Asistencia %" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
