import { DollarSign, TrendingUp, TrendingDown, Download, Filter } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Progress } from '../ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { 
  AreaChart, 
  Area, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line
} from 'recharts';

const cashFlowData = [
  { month: 'Ene', income: 45000, expenses: 32000, balance: 13000 },
  { month: 'Feb', income: 52000, expenses: 35000, balance: 17000 },
  { month: 'Mar', income: 48000, expenses: 33000, balance: 15000 },
  { month: 'Abr', income: 61000, expenses: 38000, balance: 23000 },
  { month: 'May', income: 55000, expenses: 36000, balance: 19000 },
  { month: 'Jun', income: 67000, expenses: 40000, balance: 27000 },
];

const pendingPayments = [
  { id: 1, patient: 'Carlos González', amount: 850, dueDate: '2025-11-02', status: 'overdue' },
  { id: 2, patient: 'María Rodríguez', amount: 1200, dueDate: '2025-11-05', status: 'pending' },
  { id: 3, patient: 'Luis Martínez', amount: 750, dueDate: '2025-11-08', status: 'pending' },
];

const recentTransactions = [
  { id: 1, type: 'income', description: 'Pago de terapia - Ana Sánchez', amount: 1200, date: '2025-10-30' },
  { id: 2, type: 'expense', description: 'Compra de material didáctico', amount: -450, date: '2025-10-29' },
  { id: 3, type: 'income', description: 'Pago de terapia - Pedro Gómez', amount: 900, date: '2025-10-29' },
  { id: 4, type: 'expense', description: 'Mantenimiento de equipo', amount: -800, date: '2025-10-28' },
];

export function FinanceModule() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Finanzas y ERP</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Control financiero, ingresos, egresos y flujo de caja
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Filter className="w-4 h-4 mr-2" />
            Filtrar
          </Button>
          <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
            <Download className="w-4 h-4 mr-2" />
            Exportar Reporte
          </Button>
        </div>
      </div>

      {/* Financial KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Ingresos del Mes</p>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">$67,000</h3>
            <p className="text-xs text-green-600">+22% vs mes anterior</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Egresos del Mes</p>
              <TrendingDown className="w-5 h-5 text-red-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">$40,000</h3>
            <p className="text-xs text-red-600">+8% vs mes anterior</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Balance Neto</p>
              <DollarSign className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">$27,000</h3>
            <Progress value={67.5} className="h-2 mt-2" />
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Pagos Pendientes</p>
              <Badge className="bg-orange-100 text-orange-700">3</Badge>
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">$2,800</h3>
            <p className="text-xs text-gray-500">1 vencido</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="bg-gray-100 dark:bg-gray-800">
          <TabsTrigger value="overview">Resumen</TabsTrigger>
          <TabsTrigger value="pending">Pagos Pendientes</TabsTrigger>
          <TabsTrigger value="transactions">Transacciones</TabsTrigger>
          <TabsTrigger value="analytics">Análisis</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Cash Flow Chart */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Flujo de Caja</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <AreaChart data={cashFlowData}>
                    <defs>
                      <linearGradient id="colorIncome" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4CAF50" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#4CAF50" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorExpenses" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#FF9800" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#FF9800" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
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
                    <Area 
                      type="monotone" 
                      dataKey="income" 
                      stroke="#4CAF50" 
                      fillOpacity={1} 
                      fill="url(#colorIncome)" 
                      name="Ingresos"
                    />
                    <Area 
                      type="monotone" 
                      dataKey="expenses" 
                      stroke="#FF9800" 
                      fillOpacity={1} 
                      fill="url(#colorExpenses)" 
                      name="Egresos"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* Balance Chart */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Balance Mensual</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={cashFlowData}>
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
                    <Bar dataKey="balance" fill="#4CAF50" radius={[8, 8, 0, 0]} name="Balance" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Quick Stats */}
          <Card className="border-gray-200 dark:border-gray-800 bg-gradient-to-br from-[#E8F5E9] to-white dark:from-[#2E7D32]/10 dark:to-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Estadísticas Rápidas</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Ingreso Promedio por Sesión</p>
                  <h3 className="text-gray-900 dark:text-white">$173</h3>
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Tasa de Cobro</p>
                  <h3 className="text-gray-900 dark:text-white">96%</h3>
                  <Progress value={96} className="h-2 mt-2" />
                </div>
                <div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Margen de Beneficio</p>
                  <h3 className="text-gray-900 dark:text-white">40.3%</h3>
                  <p className="text-xs text-green-600 mt-1">+3.2% vs mes anterior</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Pending Payments Tab */}
        <TabsContent value="pending">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Pagos Pendientes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {pendingPayments.map((payment) => (
                  <div 
                    key={payment.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-all"
                  >
                    <div className="flex-1">
                      <h4 className="text-sm text-gray-900 dark:text-white mb-1">{payment.patient}</h4>
                      <p className="text-xs text-gray-500">Vencimiento: {payment.dueDate}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm text-gray-900 dark:text-white">${payment.amount.toLocaleString()}</p>
                        {payment.status === 'overdue' ? (
                          <Badge className="bg-red-100 text-red-700 border-red-200 mt-1">Vencido</Badge>
                        ) : (
                          <Badge className="bg-yellow-100 text-yellow-700 border-yellow-200 mt-1">Pendiente</Badge>
                        )}
                      </div>
                      <Button size="sm" className="bg-[#4CAF50] text-white">
                        Registrar Pago
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transactions Tab */}
        <TabsContent value="transactions">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Transacciones Recientes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {recentTransactions.map((transaction) => (
                  <div 
                    key={transaction.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center gap-3 flex-1">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                        transaction.type === 'income' 
                          ? 'bg-green-100 dark:bg-green-900/20' 
                          : 'bg-red-100 dark:bg-red-900/20'
                      }`}>
                        {transaction.type === 'income' ? (
                          <TrendingUp className="w-5 h-5 text-green-600" />
                        ) : (
                          <TrendingDown className="w-5 h-5 text-red-600" />
                        )}
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm text-gray-900 dark:text-white mb-1">{transaction.description}</h4>
                        <p className="text-xs text-gray-500">{transaction.date}</p>
                      </div>
                    </div>
                    <p className={`text-sm ${
                      transaction.type === 'income' ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {transaction.amount > 0 ? '+' : ''}${Math.abs(transaction.amount).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Análisis de Rentabilidad</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={cashFlowData}>
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
                  <Line 
                    type="monotone" 
                    dataKey="income" 
                    stroke="#4CAF50" 
                    strokeWidth={3}
                    dot={{ fill: '#4CAF50', r: 5 }}
                    name="Ingresos"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="expenses" 
                    stroke="#FF9800" 
                    strokeWidth={3}
                    dot={{ fill: '#FF9800', r: 5 }}
                    name="Egresos"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="balance" 
                    stroke="#2E7D32" 
                    strokeWidth={3}
                    dot={{ fill: '#2E7D32', r: 5 }}
                    name="Balance"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
