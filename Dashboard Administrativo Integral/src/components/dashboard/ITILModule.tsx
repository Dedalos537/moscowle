import { useState } from 'react';
import { AlertCircle, Plus, TrendingUp, CheckCircle, Clock, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const incidents = [
  {
    id: 'INC-001',
    title: 'Material faltante en Sala 3',
    category: 'Materiales',
    priority: 'high',
    status: 'open',
    reporter: 'Dra. Ana Pérez',
    date: '2025-10-28',
    description: 'Faltan bloques sensoriales para terapia ocupacional'
  },
  {
    id: 'INC-002',
    title: 'Equipo de cómputo presenta fallas',
    category: 'Tecnología',
    priority: 'medium',
    status: 'analysis',
    reporter: 'Lic. Roberto Díaz',
    date: '2025-10-27',
    description: 'Computadora en Sala 2 no enciende'
  },
  {
    id: 'INC-003',
    title: 'Aire acondicionado Sala 1 no funciona',
    category: 'Infraestructura',
    priority: 'high',
    status: 'resolved',
    reporter: 'Dr. Juan López',
    date: '2025-10-25',
    description: 'Temperatura elevada afecta sesiones'
  },
  {
    id: 'INC-004',
    title: 'Solicitud de actualización de protocolos',
    category: 'Procesos',
    priority: 'low',
    status: 'validated',
    reporter: 'Dra. Laura Méndez',
    date: '2025-10-24',
    description: 'Actualizar procedimientos de evaluación inicial'
  },
];

const trendData = [
  { month: 'May', incidents: 12, resolved: 10 },
  { month: 'Jun', incidents: 15, resolved: 13 },
  { month: 'Jul', incidents: 9, resolved: 9 },
  { month: 'Ago', incidents: 18, resolved: 16 },
  { month: 'Sep', incidents: 11, resolved: 10 },
  { month: 'Oct', incidents: 14, resolved: 12 },
];

const categoryData = [
  { name: 'Materiales', value: 35, color: '#4CAF50' },
  { name: 'Tecnología', value: 25, color: '#2E7D32' },
  { name: 'Infraestructura', value: 20, color: '#8BC34A' },
  { name: 'Procesos', value: 20, color: '#A5D6A7' },
];

const statusConfig = {
  open: { label: 'Abierto', color: 'bg-red-100 text-red-700 border-red-200', icon: AlertCircle },
  analysis: { label: 'En Análisis', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: Clock },
  resolved: { label: 'Resuelto', color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
  validated: { label: 'Validado', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: CheckCircle },
};

const priorityConfig = {
  low: { label: 'Baja', color: 'bg-gray-100 text-gray-700' },
  medium: { label: 'Media', color: 'bg-orange-100 text-orange-700' },
  high: { label: 'Alta', color: 'bg-red-100 text-red-700' },
};

export function ITILModule() {
  const [filter, setFilter] = useState('all');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Mejora Continua (ITIL)</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Gestión de incidencias, problemas y procesos de mejora
          </p>
        </div>
        <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
          <Plus className="w-4 h-4 mr-2" />
          Nueva Incidencia
        </Button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Incidencias Activas</p>
              <AlertCircle className="w-5 h-5 text-red-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">8</h3>
            <Progress value={65} className="h-2" />
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">En Análisis</p>
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">5</h3>
            <p className="text-xs text-gray-500">Tiempo promedio: 2.3 días</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Resueltas este mes</p>
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">12</h3>
            <p className="text-xs text-green-600">+20% vs mes anterior</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Índice de Satisfacción</p>
              <TrendingUp className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">94%</h3>
            <Progress value={94} className="h-2" />
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="incidents" className="space-y-6">
        <TabsList className="bg-gray-100 dark:bg-gray-800">
          <TabsTrigger value="incidents">Incidencias</TabsTrigger>
          <TabsTrigger value="analytics">Análisis y Tendencias</TabsTrigger>
          <TabsTrigger value="reports">Reportes Mensuales</TabsTrigger>
        </TabsList>

        {/* Incidents Tab */}
        <TabsContent value="incidents" className="space-y-4">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-gray-900 dark:text-white">Lista de Incidencias</CardTitle>
                <Select value={filter} onValueChange={setFilter}>
                  <SelectTrigger className="w-48">
                    <SelectValue placeholder="Filtrar por estado" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas</SelectItem>
                    <SelectItem value="open">Abiertas</SelectItem>
                    <SelectItem value="analysis">En Análisis</SelectItem>
                    <SelectItem value="resolved">Resueltas</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {incidents.map((incident) => {
                  const status = statusConfig[incident.status as keyof typeof statusConfig];
                  const priority = priorityConfig[incident.priority as keyof typeof priorityConfig];
                  const StatusIcon = status.icon;

                  return (
                    <div 
                      key={incident.id}
                      className="p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-start gap-3 flex-1">
                          <StatusIcon className="w-5 h-5 text-gray-400 mt-1" />
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h4 className="text-sm text-gray-900 dark:text-white">{incident.title}</h4>
                              <Badge className="text-xs" variant="outline">{incident.id}</Badge>
                            </div>
                            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
                              {incident.description}
                            </p>
                            <div className="flex items-center gap-3 text-xs text-gray-500">
                              <span>Reportado por: {incident.reporter}</span>
                              <span>•</span>
                              <span>{incident.date}</span>
                              <span>•</span>
                              <Badge variant="outline" className="text-xs">{incident.category}</Badge>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={priority.color}>{priority.label}</Badge>
                          <Badge className={status.color}>{status.label}</Badge>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Trend Chart */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Tendencia de Incidencias</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="month" stroke="#666" />
                    <YAxis stroke="#666" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px'
                      }} 
                    />
                    <Bar dataKey="incidents" fill="#FF9800" radius={[8, 8, 0, 0]} name="Reportadas" />
                    <Bar dataKey="resolved" fill="#4CAF50" radius={[8, 8, 0, 0]} name="Resueltas" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Category Distribution */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Distribución por Categoría</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <ResponsiveContainer width="50%" height={250}>
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={100}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {categoryData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-3 flex-1">
                    {categoryData.map((category) => (
                      <div key={category.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: category.color }}
                          />
                          <span className="text-sm text-gray-700 dark:text-gray-300">{category.name}</span>
                        </div>
                        <span className="text-sm text-gray-900 dark:text-white">{category.value}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* KPIs */}
          <Card className="border-gray-200 dark:border-gray-800 bg-gradient-to-br from-[#E8F5E9] to-white dark:from-[#2E7D32]/10 dark:to-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Indicadores de Rendimiento</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Tiempo Promedio de Resolución</p>
                  <h3 className="text-gray-900 dark:text-white mb-1">3.2 días</h3>
                  <Progress value={68} className="h-2" />
                  <p className="text-xs text-green-600 mt-1">-15% vs mes anterior</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Tasa de Primera Resolución</p>
                  <h3 className="text-gray-900 dark:text-white mb-1">76%</h3>
                  <Progress value={76} className="h-2" />
                  <p className="text-xs text-green-600 mt-1">+8% vs mes anterior</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Incidencias Recurrentes</p>
                  <h3 className="text-gray-900 dark:text-white mb-1">12%</h3>
                  <Progress value={12} className="h-2" />
                  <p className="text-xs text-green-600 mt-1">-5% vs mes anterior</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Reports Tab */}
        <TabsContent value="reports">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Reportes Mensuales</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {['Octubre 2025', 'Septiembre 2025', 'Agosto 2025'].map((month, index) => (
                  <div key={index} className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700">
                    <div>
                      <h4 className="text-sm text-gray-900 dark:text-white mb-1">Reporte de {month}</h4>
                      <p className="text-xs text-gray-500">14 incidencias • 12 resueltas • 92% efectividad</p>
                    </div>
                    <Button variant="outline" size="sm">Descargar PDF</Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
