import { useState } from 'react';
import { FileText, Plus, Download, Eye, Filter, Upload, CheckCircle, Clock, AlertCircle, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { toast } from 'sonner';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

const reports = [
  {
    id: 1,
    patient: 'Carlos González',
    therapist: 'Dra. Ana Pérez',
    therapy: 'Lenguaje',
    date: '2025-10-28',
    status: 'approved',
    period: 'Octubre 2025',
    progress: 85,
    areas: {
      cognitive: 88,
      social: 82,
      emotional: 85,
      motor: 80,
      language: 90
    }
  },
  {
    id: 2,
    patient: 'María Rodríguez',
    therapist: 'Lic. Roberto Díaz',
    therapy: 'Ocupacional',
    date: '2025-10-27',
    status: 'pending',
    period: 'Octubre 2025',
    progress: 78,
    areas: {
      cognitive: 75,
      social: 80,
      emotional: 78,
      motor: 85,
      language: 72
    }
  },
  {
    id: 3,
    patient: 'Luis Martínez',
    therapist: 'Dr. Juan López',
    therapy: 'Física',
    date: '2025-10-25',
    status: 'review',
    period: 'Octubre 2025',
    progress: 92,
    areas: {
      cognitive: 88,
      social: 90,
      emotional: 92,
      motor: 95,
      language: 85
    }
  },
];

const statusConfig = {
  approved: { label: 'Aprobado', color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
  pending: { label: 'Pendiente', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: Clock },
  review: { label: 'En Revisión', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: AlertCircle },
};

const progressData = [
  { month: 'Jun', progress: 65 },
  { month: 'Jul', progress: 70 },
  { month: 'Ago', progress: 75 },
  { month: 'Sep', progress: 80 },
  { month: 'Oct', progress: 85 },
];

export function ReportsModule() {
  const [selectedReport, setSelectedReport] = useState(reports[0]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');

  const handleCreateReport = () => {
    toast.success('Informe creado exitosamente');
    setIsCreateOpen(false);
  };

  const handleApproveReport = (id: number) => {
    toast.success('Informe aprobado');
  };

  const handleDownloadReport = (id: number) => {
    toast.success('Descargando informe en PDF...');
  };

  const radarData = [
    { area: 'Cognitivo', value: selectedReport.areas.cognitive },
    { area: 'Social', value: selectedReport.areas.social },
    { area: 'Emocional', value: selectedReport.areas.emotional },
    { area: 'Motor', value: selectedReport.areas.motor },
    { area: 'Lenguaje', value: selectedReport.areas.language },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Informes y Evaluaciones</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Reportes de progreso creados por terapeutas y evaluaciones de pacientes
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
              <Plus className="w-4 h-4 mr-2" />
              Crear Informe
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Crear Nuevo Informe de Progreso</DialogTitle>
              <DialogDescription>
                Complete los datos del informe de evaluación del paciente
              </DialogDescription>
            </DialogHeader>
            <ScrollArea className="max-h-[500px] pr-4">
              <div className="space-y-4 py-4">
                <div className="grid grid-cols-2 gap-4">
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
                    <Label>Terapeuta Responsable</Label>
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
                </div>

                <div className="space-y-2">
                  <Label>Tipo de Terapia</Label>
                  <Select>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccionar tipo" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="language">Lenguaje</SelectItem>
                      <SelectItem value="occupational">Ocupacional</SelectItem>
                      <SelectItem value="physical">Física</SelectItem>
                      <SelectItem value="psychological">Psicológica</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Período de Evaluación</Label>
                  <Input type="text" placeholder="Ej: Octubre 2025" />
                </div>

                <Separator />

                <div className="space-y-3">
                  <h4 className="text-sm text-gray-900 dark:text-white">Evaluación por Áreas (0-100)</h4>
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-2">
                      <Label>Área Cognitiva</Label>
                      <Input type="number" min="0" max="100" placeholder="0-100" />
                    </div>
                    <div className="space-y-2">
                      <Label>Área Social</Label>
                      <Input type="number" min="0" max="100" placeholder="0-100" />
                    </div>
                    <div className="space-y-2">
                      <Label>Área Emocional</Label>
                      <Input type="number" min="0" max="100" placeholder="0-100" />
                    </div>
                    <div className="space-y-2">
                      <Label>Área Motora</Label>
                      <Input type="number" min="0" max="100" placeholder="0-100" />
                    </div>
                    <div className="space-y-2">
                      <Label>Área de Lenguaje</Label>
                      <Input type="number" min="0" max="100" placeholder="0-100" />
                    </div>
                  </div>
                </div>

                <Separator />

                <div className="space-y-2">
                  <Label>Observaciones Generales</Label>
                  <Textarea 
                    placeholder="Describa el progreso, logros y áreas de mejora del paciente..."
                    className="min-h-[120px]"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Recomendaciones</Label>
                  <Textarea 
                    placeholder="Recomendaciones para el siguiente período..."
                    className="min-h-[80px]"
                  />
                </div>

                <div className="space-y-2">
                  <Label>Adjuntar Archivos (opcional)</Label>
                  <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-6 text-center">
                    <Upload className="w-8 h-8 text-gray-400 mx-auto mb-2" />
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Arrastra archivos o haz clic para seleccionar
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      PDF, DOCX, imágenes (máx. 10MB)
                    </p>
                  </div>
                </div>
              </div>
            </ScrollArea>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancelar
              </Button>
              <Button 
                className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white"
                onClick={handleCreateReport}
              >
                Crear Informe
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Informes del Mes</p>
              <FileText className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">42</h3>
            <p className="text-xs text-green-600">+15% vs mes anterior</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Pendientes Revisión</p>
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">8</h3>
            <p className="text-xs text-gray-500">2 próximos a vencer</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Aprobados</p>
              <CheckCircle className="w-5 h-5 text-green-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">34</h3>
            <Progress value={81} className="h-2 mt-2" />
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Progreso Promedio</p>
              <TrendingUp className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">85%</h3>
            <p className="text-xs text-green-600">+8% vs trimestre anterior</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Reports List */}
        <Card className="lg:col-span-1 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader>
            <CardTitle className="text-gray-900 dark:text-white">Lista de Informes</CardTitle>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="mt-3">
                <SelectValue placeholder="Filtrar por estado" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos</SelectItem>
                <SelectItem value="approved">Aprobados</SelectItem>
                <SelectItem value="pending">Pendientes</SelectItem>
                <SelectItem value="review">En Revisión</SelectItem>
              </SelectContent>
            </Select>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[600px]">
              <div className="space-y-2 px-4 pb-4">
                {reports.map((report) => {
                  const status = statusConfig[report.status as keyof typeof statusConfig];
                  const StatusIcon = status.icon;
                  const isSelected = selectedReport.id === report.id;

                  return (
                    <button
                      key={report.id}
                      onClick={() => setSelectedReport(report)}
                      className={`w-full text-left p-4 rounded-lg border transition-all ${
                        isSelected
                          ? 'bg-[#E8F5E9] dark:bg-[#2E7D32]/20 border-[#4CAF50] ring-2 ring-[#4CAF50]/20'
                          : 'border-gray-200 dark:border-gray-700 hover:shadow-md'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex-1">
                          <h4 className="text-sm text-gray-900 dark:text-white mb-1">
                            {report.patient}
                          </h4>
                          <p className="text-xs text-gray-600 dark:text-gray-400">
                            {report.therapist}
                          </p>
                        </div>
                        <Badge className={status.color}>
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {status.label}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center justify-between mt-3">
                        <Badge variant="outline" className="text-xs">
                          {report.therapy}
                        </Badge>
                        <span className="text-xs text-gray-500">{report.date}</span>
                      </div>

                      <div className="mt-3">
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-gray-600 dark:text-gray-400">Progreso</span>
                          <span className="text-gray-900 dark:text-white">{report.progress}%</span>
                        </div>
                        <Progress value={report.progress} className="h-1.5" />
                      </div>
                    </button>
                  );
                })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Report Detail */}
        <Card className="lg:col-span-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader className="border-b border-gray-200 dark:border-gray-800">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="text-gray-900 dark:text-white mb-2">
                  Informe de Progreso - {selectedReport.patient}
                </CardTitle>
                <div className="flex items-center gap-3 flex-wrap">
                  <Badge variant="outline">{selectedReport.therapy}</Badge>
                  <Badge variant="outline">{selectedReport.period}</Badge>
                  <span className="text-sm text-gray-500">
                    Por: {selectedReport.therapist}
                  </span>
                </div>
              </div>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleDownloadReport(selectedReport.id)}
                >
                  <Download className="w-4 h-4 mr-2" />
                  PDF
                </Button>
                {selectedReport.status === 'pending' && (
                  <Button 
                    size="sm"
                    className="bg-[#4CAF50] text-white"
                    onClick={() => handleApproveReport(selectedReport.id)}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Aprobar
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <Tabs defaultValue="overview" className="space-y-6">
              <TabsList>
                <TabsTrigger value="overview">Resumen</TabsTrigger>
                <TabsTrigger value="areas">Áreas de Desarrollo</TabsTrigger>
                <TabsTrigger value="progress">Evolución</TabsTrigger>
              </TabsList>

              {/* Overview Tab */}
              <TabsContent value="overview" className="space-y-6">
                <div>
                  <h4 className="text-sm text-gray-900 dark:text-white mb-3">Progreso General</h4>
                  <div className="flex items-center gap-4 mb-2">
                    <div className="flex-1">
                      <Progress value={selectedReport.progress} className="h-3" />
                    </div>
                    <span className="text-2xl text-gray-900 dark:text-white">{selectedReport.progress}%</span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Progreso acumulado durante el período evaluado
                  </p>
                </div>

                <Separator />

                <div>
                  <h4 className="text-sm text-gray-900 dark:text-white mb-3">Observaciones del Terapeuta</h4>
                  <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-4">
                    <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                      El paciente ha mostrado avances significativos en el área de lenguaje expresivo, 
                      demostrando mayor fluidez y vocabulario más amplio. Se observa mejor integración 
                      social con sus pares durante las actividades grupales. Se recomienda continuar 
                      con ejercicios de articulación y reforzar actividades de lectoescritura.
                    </p>
                  </div>
                </div>

                <div>
                  <h4 className="text-sm text-gray-900 dark:text-white mb-3">Recomendaciones</h4>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-[#4CAF50] mt-0.5" />
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        Continuar con sesiones 2 veces por semana
                      </p>
                    </div>
                    <div className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-[#4CAF50] mt-0.5" />
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        Incorporar ejercicios de lectura en casa
                      </p>
                    </div>
                    <div className="flex items-start gap-2">
                      <CheckCircle className="w-4 h-4 text-[#4CAF50] mt-0.5" />
                      <p className="text-sm text-gray-700 dark:text-gray-300">
                        Fomentar interacción social con compañeros
                      </p>
                    </div>
                  </div>
                </div>
              </TabsContent>

              {/* Areas Tab */}
              <TabsContent value="areas" className="space-y-6">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <div>
                    <h4 className="text-sm text-gray-900 dark:text-white mb-4">Evaluación por Áreas</h4>
                    <div className="space-y-4">
                      {Object.entries(selectedReport.areas).map(([area, value]) => (
                        <div key={area}>
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                              {area === 'cognitive' ? 'Cognitivo' :
                               area === 'social' ? 'Social' :
                               area === 'emotional' ? 'Emocional' :
                               area === 'motor' ? 'Motor' :
                               'Lenguaje'}
                            </span>
                            <span className="text-sm text-gray-900 dark:text-white">{value}%</span>
                          </div>
                          <Progress value={value} className="h-2" />
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h4 className="text-sm text-gray-900 dark:text-white mb-4">Gráfico Radar</h4>
                    <ResponsiveContainer width="100%" height={250}>
                      <RadarChart data={radarData}>
                        <PolarGrid stroke="#e0e0e0" />
                        <PolarAngleAxis dataKey="area" stroke="#666" />
                        <PolarRadiusAxis angle={90} domain={[0, 100]} stroke="#666" />
                        <Radar 
                          name="Desarrollo" 
                          dataKey="value" 
                          stroke="#4CAF50" 
                          fill="#4CAF50" 
                          fillOpacity={0.5}
                        />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </TabsContent>

              {/* Progress Tab */}
              <TabsContent value="progress">
                <div>
                  <h4 className="text-sm text-gray-900 dark:text-white mb-4">Evolución del Progreso</h4>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={progressData}>
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
                      <Line 
                        type="monotone" 
                        dataKey="progress" 
                        stroke="#4CAF50" 
                        strokeWidth={3}
                        dot={{ fill: '#4CAF50', r: 6 }}
                        name="Progreso %"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
