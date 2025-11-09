import { Users, Calendar, DollarSign, TrendingUp, Activity, AlertTriangle } from 'lucide-react';
import { StatsCard } from './StatsCard';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Progress } from '../ui/progress';
import { Badge } from '../ui/badge';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';

const revenueData = [
  { month: 'Ene', income: 45000, expenses: 32000 },
  { month: 'Feb', income: 52000, expenses: 35000 },
  { month: 'Mar', income: 48000, expenses: 33000 },
  { month: 'Abr', income: 61000, expenses: 38000 },
  { month: 'May', income: 55000, expenses: 36000 },
  { month: 'Jun', income: 67000, expenses: 40000 },
];

const therapyDistribution = [
  { name: 'Lenguaje', value: 35, color: '#4CAF50' },
  { name: 'Ocupacional', value: 28, color: '#8BC34A' },
  { name: 'Física', value: 22, color: '#2E7D32' },
  { name: 'Psicológica', value: 15, color: '#A5D6A7' },
];

const attendanceData = [
  { day: 'Lun', attendance: 92 },
  { day: 'Mar', attendance: 88 },
  { day: 'Mié', attendance: 95 },
  { day: 'Jue', attendance: 91 },
  { day: 'Vie', attendance: 87 },
];

const recentActivities = [
  { id: 1, type: 'session', text: 'Sesión completada: Ana Martínez - Terapia de Lenguaje', time: '10 min', status: 'success' },
  { id: 2, type: 'payment', text: 'Pago recibido: $850 - Luis Hernández', time: '25 min', status: 'success' },
  { id: 3, type: 'incident', text: 'Incidencia reportada: Material faltante en Sala 3', time: '1 hr', status: 'warning' },
  { id: 4, type: 'message', text: 'Nuevo mensaje de padre: María González', time: '2 hrs', status: 'info' },
];

export function DashboardHome() {
  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatsCard
          title="Pacientes Activos"
          value="142"
          change="+12% vs mes anterior"
          changeType="positive"
          icon={Users}
        />
        <StatsCard
          title="Sesiones del Mes"
          value="387"
          change="+8% vs mes anterior"
          changeType="positive"
          icon={Calendar}
        />
        <StatsCard
          title="Ingresos del Mes"
          value="$67,000"
          change="+22% vs mes anterior"
          changeType="positive"
          icon={DollarSign}
          iconBgColor="bg-blue-50 dark:bg-blue-900/20"
          iconColor="text-blue-600"
        />
        <StatsCard
          title="Tasa de Asistencia"
          value="91%"
          change="+3% vs mes anterior"
          changeType="positive"
          icon={TrendingUp}
          iconBgColor="bg-purple-50 dark:bg-purple-900/20"
          iconColor="text-purple-600"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Ingresos vs Egresos</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={revenueData}>
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
                <Bar dataKey="income" fill="#4CAF50" radius={[8, 8, 0, 0]} />
                <Bar dataKey="expenses" fill="#FF9800" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Therapy Distribution */}
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Distribución de Terapias</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <ResponsiveContainer width="50%" height={200}>
                <PieChart>
                  <Pie
                    data={therapyDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {therapyDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-3 flex-1">
                {therapyDistribution.map((therapy) => (
                  <div key={therapy.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div 
                        className="w-3 h-3 rounded-full" 
                        style={{ backgroundColor: therapy.color }}
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300">{therapy.name}</span>
                    </div>
                    <span className="text-sm text-gray-900 dark:text-white">{therapy.value}%</span>
                  </div>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Attendance Trend */}
        <Card className="lg:col-span-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Asistencia Semanal</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={attendanceData}>
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
                  dataKey="attendance" 
                  stroke="#4CAF50" 
                  strokeWidth={3}
                  dot={{ fill: '#4CAF50', r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Actividad Reciente</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex gap-3">
                  <div className={`w-2 h-2 mt-1.5 rounded-full flex-shrink-0 ${
                    activity.status === 'success' ? 'bg-[#4CAF50]' :
                    activity.status === 'warning' ? 'bg-orange-500' :
                    'bg-blue-500'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-gray-700 dark:text-gray-300">{activity.text}</p>
                    <p className="text-xs text-gray-500 mt-1">{activity.time} atrás</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="border-gray-200 dark:border-gray-800 bg-gradient-to-br from-[#E8F5E9] to-white dark:from-[#2E7D32]/10 dark:to-[#1E1E2E]">
        <CardHeader>
          <CardTitle className="text-gray-900 dark:text-white">Acciones Rápidas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="p-4 rounded-xl bg-white dark:bg-[#1E1E2E] border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all">
              <Calendar className="w-8 h-8 text-[#4CAF50] mb-2" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Nueva Sesión</p>
            </button>
            <button className="p-4 rounded-xl bg-white dark:bg-[#1E1E2E] border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all">
              <Users className="w-8 h-8 text-[#4CAF50] mb-2" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Registrar Paciente</p>
            </button>
            <button className="p-4 rounded-xl bg-white dark:bg-[#1E1E2E] border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all">
              <DollarSign className="w-8 h-8 text-[#4CAF50] mb-2" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Registrar Pago</p>
            </button>
            <button className="p-4 rounded-xl bg-white dark:bg-[#1E1E2E] border border-gray-200 dark:border-gray-700 hover:shadow-lg transition-all">
              <AlertTriangle className="w-8 h-8 text-[#4CAF50] mb-2" />
              <p className="text-sm text-gray-700 dark:text-gray-300">Nueva Incidencia</p>
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
