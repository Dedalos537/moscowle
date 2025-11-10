import { useState, useEffect } from 'react';
import { MessageSquare, Search, Filter, Star, Reply, Archive, MoreVertical, Loader2, RefreshCw, Clock, AlertCircle, Eye, Send } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Avatar, AvatarFallback } from '../ui/avatar';
import { Textarea } from '../ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import { ScrollArea } from '../ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../ui/table';

// Tipos de datos
interface ContactInquiry {
  id: number;
  inquiry_code: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  subject?: string;
  message: string;
  service_interest?: string;
  urgency: 'low' | 'medium' | 'high';
  status: 'new' | 'contacted' | 'in_progress' | 'resolved' | 'closed';
  created_at: string;
  updated_at: string;
}

interface Message {
  id: number;
  conversation_id?: number;
  inquiry_id?: number;
  sender_type: 'user' | 'anonymous' | 'system';
  sender_name?: string;
  sender_email?: string;
  message_text: string;
  message_type: 'text' | 'file' | 'image' | 'system';
  is_read: boolean;
  created_at: string;
}

interface Stats {
  total_inquiries: number;
  new_inquiries_24h: number;
  pending_inquiries: number;
  unread_messages: number;
}

// Configuración de la API
const API_BASE_URL = 'http://127.0.0.1:8001';
const getAuthToken = () => localStorage.getItem('auth_token');

// Funciones de API
const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const token = getAuthToken();
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.statusText}`);
  }

  return response.json();
};

export function MessagesModule() {
  // Estados principales
  const [stats, setStats] = useState<Stats>({
    total_inquiries: 0,
    new_inquiries_24h: 0,
    pending_inquiries: 0,
    unread_messages: 0,
  });

  const [inquiries, setInquiries] = useState<ContactInquiry[]>([]);
  const [selectedInquiry, setSelectedInquiry] = useState<ContactInquiry | null>(null);

  // Estados de UI
  const [isLoading, setIsLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [replyText, setReplyText] = useState('');
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);

  // Cargar estadísticas
  const loadStats = async () => {
    try {
      const data = await apiCall('/admin/stats');
      setStats(data);
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  // Cargar consultas
  const loadInquiries = async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (searchTerm) params.append('search', searchTerm);
      params.append('per_page', '50');

      const data = await apiCall(`/admin/inquiries?${params}`);
      setInquiries(data.items || []);
    } catch (error) {
      console.error('Error loading inquiries:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Actualizar estado de consulta
  const updateInquiryStatus = async (inquiryId: number, status: string) => {
    try {
      await apiCall(`/admin/inquiries/${inquiryId}`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      });
      await loadInquiries();
    } catch (error) {
      console.error('Error updating inquiry:', error);
    }
  };

  // Responder a una consulta
  const sendReply = async () => {
    if (!replyText.trim() || !selectedInquiry) return;

    setIsSubmittingReply(true);
    try {
      await apiCall('/admin/messages', {
        method: 'POST',
        body: JSON.stringify({
          inquiry_id: selectedInquiry.id,
          message_text: replyText,
          is_internal: false,
        }),
      });

      setReplyText('');
      await updateInquiryStatus(selectedInquiry.id, 'contacted');
    } catch (error) {
      console.error('Error sending reply:', error);
    } finally {
      setIsSubmittingReply(false);
    }
  };

  // Efectos
  useEffect(() => {
    loadStats();
    loadInquiries();
  }, []);

  useEffect(() => {
    loadInquiries();
  }, [searchTerm, statusFilter]);

  // Utilidades
  const getUrgencyColor = (urgency: string) => {
    switch (urgency) {
      case 'high': return 'bg-red-100 text-red-700';
      case 'medium': return 'bg-yellow-100 text-yellow-700';
      case 'low': return 'bg-green-100 text-green-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new': return 'bg-blue-100 text-blue-700';
      case 'contacted': return 'bg-purple-100 text-purple-700';
      case 'in_progress': return 'bg-orange-100 text-orange-700';
      case 'resolved': return 'bg-green-100 text-green-700';
      case 'closed': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Mensajería y Consultas</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Gestiona mensajes y consultas de contacto desde la web
          </p>
        </div>
        <Button 
          onClick={() => {
            loadStats();
            loadInquiries();
          }}
          variant="outline"
          className="gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Actualizar
        </Button>
      </div>

      {/* Estadísticas */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Consultas</p>
              <MessageSquare className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-2xl text-gray-900 dark:text-white mb-1">{stats.total_inquiries}</h3>
            <p className="text-xs text-gray-500">Históricas</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Nuevas (24h)</p>
              <Clock className="w-5 h-5 text-blue-500" />
            </div>
            <h3 className="text-2xl text-gray-900 dark:text-white mb-1">{stats.new_inquiries_24h}</h3>
            <p className="text-xs text-green-600">Últimas 24 horas</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Pendientes</p>
              <AlertCircle className="w-5 h-5 text-orange-500" />
            </div>
            <h3 className="text-2xl text-gray-900 dark:text-white mb-1">{stats.pending_inquiries}</h3>
            <p className="text-xs text-orange-600">Requieren atención</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Sin Leer</p>
              <Eye className="w-5 h-5 text-red-500" />
            </div>
            <h3 className="text-2xl text-gray-900 dark:text-white mb-1">{stats.unread_messages}</h3>
            <p className="text-xs text-red-600">Mensajes nuevos</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Messages List */}
        <Card className="lg:col-span-1 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardHeader className="space-y-4">
            <CardTitle className="text-gray-900 dark:text-white">Consultas</CardTitle>
            
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input 
                placeholder="Buscar consultas..." 
                className="pl-10"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            {/* Filter */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="Filtrar por estado..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las consultas</SelectItem>
                <SelectItem value="new">Nuevas</SelectItem>
                <SelectItem value="contacted">Contactadas</SelectItem>
                <SelectItem value="in_progress">En progreso</SelectItem>
                <SelectItem value="resolved">Resueltas</SelectItem>
                <SelectItem value="closed">Cerradas</SelectItem>
              </SelectContent>
            </Select>
          </CardHeader>

          <CardContent className="p-0">
            <ScrollArea className="h-[600px]">
              <div className="space-y-1 px-4 pb-4">
                {isLoading ? (
                  <div className="flex items-center justify-center p-8">
                    <Loader2 className="w-6 h-6 animate-spin" />
                    <span className="ml-2">Cargando...</span>
                  </div>
                ) : inquiries.length === 0 ? (
                  <div className="text-center p-8 text-gray-500">
                    No hay consultas disponibles
                  </div>
                ) : (
                  inquiries.map((inquiry) => (
                    <button
                      key={inquiry.id}
                      onClick={() => setSelectedInquiry(inquiry)}
                      className={`w-full text-left p-4 rounded-lg transition-all ${
                        selectedInquiry?.id === inquiry.id
                          ? 'bg-[#E8F5E9] dark:bg-[#2E7D32]/20 border-l-4 border-[#4CAF50]'
                          : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <Avatar className="w-10 h-10">
                          <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                            {inquiry.first_name[0]}{inquiry.last_name[0]}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm text-gray-900 dark:text-white">
                              {inquiry.first_name} {inquiry.last_name}
                            </span>
                            <span className="text-xs text-gray-500">
                              {formatDate(inquiry.created_at)}
                            </span>
                          </div>
                          <p className="text-sm mb-1 text-gray-900 dark:text-white">
                            {inquiry.subject || 'Sin asunto'}
                          </p>
                          <p className="text-xs text-gray-500 truncate">{inquiry.message}</p>
                          <div className="flex items-center gap-2 mt-2">
                            <Badge className={getStatusColor(inquiry.status)}>
                              {inquiry.status === 'new' ? 'Nuevo' :
                               inquiry.status === 'contacted' ? 'Contactado' :
                               inquiry.status === 'in_progress' ? 'En progreso' :
                               inquiry.status === 'resolved' ? 'Resuelto' : 'Cerrado'}
                            </Badge>
                            <Badge className={getUrgencyColor(inquiry.urgency)}>
                              {inquiry.urgency === 'high' ? 'Alta' : 
                               inquiry.urgency === 'medium' ? 'Media' : 'Baja'}
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Message Detail */}
        <Card className="lg:col-span-2 border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          {selectedInquiry ? (
            <>
              <CardHeader className="border-b border-gray-200 dark:border-gray-800">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <Avatar className="w-12 h-12">
                      <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                        {selectedInquiry.first_name[0]}{selectedInquiry.last_name[0]}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h3 className="text-gray-900 dark:text-white">
                        {selectedInquiry.subject || 'Sin asunto'}
                      </h3>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        De: {selectedInquiry.first_name} {selectedInquiry.last_name} • {formatDate(selectedInquiry.created_at)}
                      </p>
                      <div className="flex gap-2 mt-2">
                        <Badge variant="outline" className="text-xs">
                          {selectedInquiry.email}
                        </Badge>
                        {selectedInquiry.phone && (
                          <Badge variant="outline" className="text-xs">
                            {selectedInquiry.phone}
                          </Badge>
                        )}
                        {selectedInquiry.service_interest && (
                          <Badge variant="outline" className="text-xs">
                            Servicio: {selectedInquiry.service_interest}
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Select
                      value={selectedInquiry.status}
                      onValueChange={(value: string) => updateInquiryStatus(selectedInquiry.id, value)}
                    >
                      <SelectTrigger className="w-32">
                        <Badge className={getStatusColor(selectedInquiry.status)}>
                          {selectedInquiry.status === 'new' ? 'Nuevo' :
                           selectedInquiry.status === 'contacted' ? 'Contactado' :
                           selectedInquiry.status === 'in_progress' ? 'En progreso' :
                           selectedInquiry.status === 'resolved' ? 'Resuelto' : 'Cerrado'}
                        </Badge>
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="new">Nuevo</SelectItem>
                        <SelectItem value="contacted">Contactado</SelectItem>
                        <SelectItem value="in_progress">En progreso</SelectItem>
                        <SelectItem value="resolved">Resuelto</SelectItem>
                        <SelectItem value="closed">Cerrado</SelectItem>
                      </SelectContent>
                    </Select>
                    <Button variant="ghost" size="icon">
                      <Star className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <Archive className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>

              <CardContent className="p-6">
                <ScrollArea className="h-[400px] mb-6">
                  <div className="prose dark:prose-invert max-w-none">
                    <div className="bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
                      <p className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                        {selectedInquiry.message}
                      </p>
                    </div>
                    
                    <div className="mt-4 space-y-2">
                      <div className="flex gap-4">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Código:</span>
                        <span className="text-sm text-gray-900 dark:text-white">{selectedInquiry.inquiry_code}</span>
                      </div>
                      <div className="flex gap-4">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Urgencia:</span>
                        <Badge className={getUrgencyColor(selectedInquiry.urgency)}>
                          {selectedInquiry.urgency === 'high' ? 'Alta' : 
                           selectedInquiry.urgency === 'medium' ? 'Media' : 'Baja'}
                        </Badge>
                      </div>
                      {selectedInquiry.service_interest && (
                        <div className="flex gap-4">
                          <span className="text-sm text-gray-600 dark:text-gray-400">Servicio de interés:</span>
                          <span className="text-sm text-gray-900 dark:text-white">{selectedInquiry.service_interest}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </ScrollArea>

                {/* Reply Section */}
                <div className="border-t border-gray-200 dark:border-gray-800 pt-6">
                  <h4 className="text-sm text-gray-900 dark:text-white mb-3">Responder</h4>
                  <Textarea
                    placeholder="Escriba su respuesta..."
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    className="min-h-[120px] mb-4"
                  />
                  <div className="flex justify-between items-center">
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        Adjuntar archivo
                      </Button>
                      <Button variant="outline" size="sm">
                        Plantilla
                      </Button>
                    </div>
                    <Button 
                      onClick={sendReply}
                      disabled={!replyText.trim() || isSubmittingReply}
                      className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white gap-2"
                    >
                      {isSubmittingReply ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Reply className="w-4 h-4" />
                      )}
                      Enviar Respuesta
                    </Button>
                  </div>
                </div>
              </CardContent>
            </>
          ) : (
            <CardContent className="p-6">
              <div className="flex items-center justify-center h-[600px] text-gray-500">
                <div className="text-center">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>Selecciona una consulta para ver los detalles</p>
                </div>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
}
