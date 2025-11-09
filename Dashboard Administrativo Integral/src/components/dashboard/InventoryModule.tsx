import { useState } from 'react';
import { Package, Plus, Search, AlertTriangle, Download, TrendingDown, CheckCircle, Clock, Edit, Trash2, Archive } from 'lucide-react';
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
} from '../ui/dialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../ui/alert-dialog';
import { Label } from '../ui/label';
import { Textarea } from '../ui/textarea';
import { ScrollArea } from '../ui/scroll-area';
import { Separator } from '../ui/separator';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

interface InventoryItem {
  id: number;
  name: string;
  category: 'therapeutic' | 'didactic' | 'equipment' | 'supplies' | 'sensory';
  quantity: number;
  minStock: number;
  maxStock: number;
  unit: string;
  location: string;
  responsible: string;
  expiryDate?: string;
  status: 'available' | 'low' | 'critical' | 'expired';
  lastUpdate: string;
  cost: number;
}

const initialInventory: InventoryItem[] = [
  {
    id: 1,
    name: 'Bloques Sensoriales',
    category: 'sensory',
    quantity: 8,
    minStock: 10,
    maxStock: 30,
    unit: 'sets',
    location: 'Sala 3 - Estante A',
    responsible: 'Lic. Roberto Díaz',
    status: 'low',
    lastUpdate: '2025-10-25',
    cost: 450
  },
  {
    id: 2,
    name: 'Material de Lectoescritura',
    category: 'didactic',
    quantity: 25,
    minStock: 15,
    maxStock: 40,
    unit: 'paquetes',
    location: 'Sala 1 - Armario B',
    responsible: 'Dra. Ana Pérez',
    status: 'available',
    lastUpdate: '2025-10-28',
    cost: 320
  },
  {
    id: 3,
    name: 'Pelotas de Terapia Física',
    category: 'therapeutic',
    quantity: 12,
    minStock: 8,
    maxStock: 20,
    unit: 'unidades',
    location: 'Sala 4 - Gimnasio',
    responsible: 'Dr. Juan López',
    status: 'available',
    lastUpdate: '2025-10-27',
    cost: 280
  },
  {
    id: 4,
    name: 'Gel Antibacterial',
    category: 'supplies',
    quantity: 3,
    minStock: 10,
    maxStock: 30,
    unit: 'litros',
    location: 'Almacén General',
    responsible: 'María García',
    expiryDate: '2026-03-15',
    status: 'critical',
    lastUpdate: '2025-10-29',
    cost: 180
  },
  {
    id: 5,
    name: 'Computadora Lenovo',
    category: 'equipment',
    quantity: 4,
    minStock: 3,
    maxStock: 6,
    unit: 'unidades',
    location: 'Sala 2',
    responsible: 'Dra. Laura Méndez',
    status: 'available',
    lastUpdate: '2025-10-20',
    cost: 12000
  },
  {
    id: 6,
    name: 'Juegos de Motricidad Fina',
    category: 'therapeutic',
    quantity: 6,
    minStock: 8,
    maxStock: 15,
    unit: 'sets',
    location: 'Sala 3 - Estante C',
    responsible: 'Lic. Roberto Díaz',
    status: 'low',
    lastUpdate: '2025-10-26',
    cost: 520
  },
  {
    id: 7,
    name: 'Papel Bond',
    category: 'supplies',
    quantity: 2,
    minStock: 5,
    maxStock: 20,
    unit: 'resmas',
    location: 'Almacén General',
    responsible: 'María García',
    status: 'critical',
    lastUpdate: '2025-10-30',
    cost: 150
  },
];

const categoryConfig = {
  therapeutic: { label: 'Terapéutico', color: '#4CAF50' },
  didactic: { label: 'Didáctico', color: '#8BC34A' },
  equipment: { label: 'Equipo', color: '#2E7D32' },
  supplies: { label: 'Insumos', color: '#A5D6A7' },
  sensory: { label: 'Sensorial', color: '#66BB6A' },
};

const statusConfig = {
  available: { label: 'Disponible', color: 'bg-green-100 text-green-700 border-green-200', icon: CheckCircle },
  low: { label: 'Stock Bajo', color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: AlertTriangle },
  critical: { label: 'Crítico', color: 'bg-red-100 text-red-700 border-red-200', icon: TrendingDown },
  expired: { label: 'Vencido', color: 'bg-gray-100 text-gray-700 border-gray-200', icon: Clock },
};

export function InventoryModule() {
  const [inventory, setInventory] = useState<InventoryItem[]>(initialInventory);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isMovementOpen, setIsMovementOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedItem, setSelectedItem] = useState<InventoryItem | null>(null);
  const [filterCategory, setFilterCategory] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    category: 'therapeutic' as InventoryItem['category'],
    quantity: 0,
    minStock: 0,
    maxStock: 0,
    unit: '',
    location: '',
    responsible: '',
    expiryDate: '',
    cost: 0,
  });

  const [movementData, setMovementData] = useState({
    type: 'in' as 'in' | 'out',
    quantity: 0,
    reason: '',
  });

  const handleCreateItem = () => {
    const newItem: InventoryItem = {
      id: inventory.length + 1,
      ...formData,
      status: formData.quantity <= formData.minStock ? 'critical' : 
              formData.quantity <= formData.minStock * 1.5 ? 'low' : 'available',
      lastUpdate: new Date().toISOString().split('T')[0],
      expiryDate: formData.expiryDate || undefined,
    };

    setInventory([...inventory, newItem]);
    toast.success('Material agregado al inventario');
    setIsCreateOpen(false);
    resetForm();
  };

  const handleEditItem = () => {
    if (!selectedItem) return;

    setInventory(inventory.map(item =>
      item.id === selectedItem.id
        ? {
            ...item,
            ...formData,
            status: formData.quantity <= formData.minStock ? 'critical' :
                    formData.quantity <= formData.minStock * 1.5 ? 'low' : 'available',
            lastUpdate: new Date().toISOString().split('T')[0],
          }
        : item
    ));

    toast.success('Material actualizado correctamente');
    setIsEditOpen(false);
    setSelectedItem(null);
    resetForm();
  };

  const handleMovement = () => {
    if (!selectedItem) return;

    const newQuantity = movementData.type === 'in' 
      ? selectedItem.quantity + movementData.quantity
      : selectedItem.quantity - movementData.quantity;

    if (newQuantity < 0) {
      toast.error('La cantidad resultante no puede ser negativa');
      return;
    }

    setInventory(inventory.map(item =>
      item.id === selectedItem.id
        ? {
            ...item,
            quantity: newQuantity,
            status: newQuantity <= item.minStock ? 'critical' :
                    newQuantity <= item.minStock * 1.5 ? 'low' : 'available',
            lastUpdate: new Date().toISOString().split('T')[0],
          }
        : item
    ));

    toast.success(`${movementData.type === 'in' ? 'Entrada' : 'Salida'} registrada correctamente`);
    setIsMovementOpen(false);
    setSelectedItem(null);
    setMovementData({ type: 'in', quantity: 0, reason: '' });
  };

  const handleDeleteItem = () => {
    if (!selectedItem) return;

    setInventory(inventory.filter(item => item.id !== selectedItem.id));
    toast.success('Material eliminado del inventario');
    setDeleteDialogOpen(false);
    setSelectedItem(null);
  };

  const openEditDialog = (item: InventoryItem) => {
    setSelectedItem(item);
    setFormData({
      name: item.name,
      category: item.category,
      quantity: item.quantity,
      minStock: item.minStock,
      maxStock: item.maxStock,
      unit: item.unit,
      location: item.location,
      responsible: item.responsible,
      expiryDate: item.expiryDate || '',
      cost: item.cost,
    });
    setIsEditOpen(true);
  };

  const openMovementDialog = (item: InventoryItem) => {
    setSelectedItem(item);
    setIsMovementOpen(true);
  };

  const openDeleteDialog = (item: InventoryItem) => {
    setSelectedItem(item);
    setDeleteDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      category: 'therapeutic',
      quantity: 0,
      minStock: 0,
      maxStock: 0,
      unit: '',
      location: '',
      responsible: '',
      expiryDate: '',
      cost: 0,
    });
  };

  const filteredInventory = inventory.filter(item => {
    const matchesCategory = filterCategory === 'all' || item.category === filterCategory;
    const matchesSearch = item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         item.location.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  const categoryData = Object.entries(categoryConfig).map(([key, config]) => ({
    name: config.label,
    value: inventory.filter(item => item.category === key).length,
    color: config.color,
  }));

  const stockData = [
    { status: 'Disponible', count: inventory.filter(i => i.status === 'available').length },
    { status: 'Bajo', count: inventory.filter(i => i.status === 'low').length },
    { status: 'Crítico', count: inventory.filter(i => i.status === 'critical').length },
    { status: 'Vencido', count: inventory.filter(i => i.status === 'expired').length },
  ];

  const totalValue = inventory.reduce((sum, item) => sum + (item.cost * item.quantity), 0);

  const ItemForm = ({ onSubmit, submitLabel }: { onSubmit: () => void; submitLabel: string }) => (
    <ScrollArea className="max-h-[500px] pr-4">
      <div className="space-y-4 py-4">
        <div className="space-y-2">
          <Label>Nombre del Material *</Label>
          <Input
            placeholder="Ej: Bloques Sensoriales"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Categoría *</Label>
            <Select
              value={formData.category}
              onValueChange={(value) => setFormData({ ...formData, category: value as InventoryItem['category'] })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="therapeutic">Terapéutico</SelectItem>
                <SelectItem value="didactic">Didáctico</SelectItem>
                <SelectItem value="equipment">Equipo</SelectItem>
                <SelectItem value="supplies">Insumos</SelectItem>
                <SelectItem value="sensory">Sensorial</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Unidad de Medida *</Label>
            <Input
              placeholder="Ej: sets, unidades, litros"
              value={formData.unit}
              onChange={(e) => setFormData({ ...formData, unit: e.target.value })}
            />
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label>Cantidad Actual *</Label>
            <Input
              type="number"
              min="0"
              value={formData.quantity}
              onChange={(e) => setFormData({ ...formData, quantity: parseInt(e.target.value) || 0 })}
            />
          </div>

          <div className="space-y-2">
            <Label>Stock Mínimo *</Label>
            <Input
              type="number"
              min="0"
              value={formData.minStock}
              onChange={(e) => setFormData({ ...formData, minStock: parseInt(e.target.value) || 0 })}
            />
          </div>

          <div className="space-y-2">
            <Label>Stock Máximo *</Label>
            <Input
              type="number"
              min="0"
              value={formData.maxStock}
              onChange={(e) => setFormData({ ...formData, maxStock: parseInt(e.target.value) || 0 })}
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label>Ubicación *</Label>
          <Input
            placeholder="Ej: Sala 3 - Estante A"
            value={formData.location}
            onChange={(e) => setFormData({ ...formData, location: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <Label>Responsable *</Label>
          <Select
            value={formData.responsible}
            onValueChange={(value) => setFormData({ ...formData, responsible: value })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Seleccionar responsable" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Dra. Ana Pérez">Dra. Ana Pérez</SelectItem>
              <SelectItem value="Lic. Roberto Díaz">Lic. Roberto Díaz</SelectItem>
              <SelectItem value="Dr. Juan López">Dr. Juan López</SelectItem>
              <SelectItem value="Dra. Laura Méndez">Dra. Laura Méndez</SelectItem>
              <SelectItem value="María García">María García</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Costo Unitario ($)</Label>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={formData.cost}
              onChange={(e) => setFormData({ ...formData, cost: parseFloat(e.target.value) || 0 })}
            />
          </div>

          <div className="space-y-2">
            <Label>Fecha de Caducidad (opcional)</Label>
            <Input
              type="date"
              value={formData.expiryDate}
              onChange={(e) => setFormData({ ...formData, expiryDate: e.target.value })}
            />
          </div>
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>Alertas Automáticas:</strong> El sistema generará alertas cuando el stock 
            llegue al nivel mínimo o cuando un material esté próximo a caducar.
          </p>
        </div>
      </div>

      <DialogFooter className="pt-4">
        <Button variant="outline" onClick={() => {
          setIsCreateOpen(false);
          setIsEditOpen(false);
          resetForm();
        }}>
          Cancelar
        </Button>
        <Button
          className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white"
          onClick={onSubmit}
          disabled={!formData.name || !formData.unit || !formData.location || !formData.responsible}
        >
          {submitLabel}
        </Button>
      </DialogFooter>
    </ScrollArea>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Gestión de Inventario</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Control de materiales, herramientas terapéuticas y equipamiento
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => toast.success('Exportando inventario...')}>
            <Download className="w-4 h-4 mr-2" />
            Exportar
          </Button>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
                <Plus className="w-4 h-4 mr-2" />
                Agregar Material
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>Agregar Material al Inventario</DialogTitle>
                <DialogDescription>
                  Complete la información del material. Los campos marcados con * son obligatorios.
                </DialogDescription>
              </DialogHeader>
              <ItemForm onSubmit={handleCreateItem} submitLabel="Agregar Material" />
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Items</p>
              <Package className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">{inventory.length}</h3>
            <p className="text-xs text-gray-500">{categoryData.length} categorías</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Alertas Críticas</p>
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">
              {inventory.filter(i => i.status === 'critical').length}
            </h3>
            <p className="text-xs text-red-600">Requieren reposición urgente</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Stock Bajo</p>
              <TrendingDown className="w-5 h-5 text-yellow-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">
              {inventory.filter(i => i.status === 'low').length}
            </h3>
            <p className="text-xs text-gray-500">Necesitan atención</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Valor Total</p>
              <CheckCircle className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">
              ${totalValue.toLocaleString()}
            </h3>
            <p className="text-xs text-gray-500">Inversión en inventario</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="list" className="space-y-6">
        <div className="flex items-center justify-between">
          <TabsList className="bg-gray-100 dark:bg-gray-800">
            <TabsTrigger value="list">Lista de Inventario</TabsTrigger>
            <TabsTrigger value="alerts">
              Alertas ({inventory.filter(i => i.status === 'critical' || i.status === 'low').length})
            </TabsTrigger>
            <TabsTrigger value="analytics">Análisis</TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar material..."
                className="pl-10 w-64"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <Select value={filterCategory} onValueChange={setFilterCategory}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Todas las categorías" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas las categorías</SelectItem>
                <SelectItem value="therapeutic">Terapéutico</SelectItem>
                <SelectItem value="didactic">Didáctico</SelectItem>
                <SelectItem value="equipment">Equipo</SelectItem>
                <SelectItem value="supplies">Insumos</SelectItem>
                <SelectItem value="sensory">Sensorial</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* List Tab */}
        <TabsContent value="list">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Material</TableHead>
                    <TableHead>Categoría</TableHead>
                    <TableHead>Stock</TableHead>
                    <TableHead>Ubicación</TableHead>
                    <TableHead>Responsable</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Última Act.</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredInventory.map((item) => {
                    const status = statusConfig[item.status];
                    const StatusIcon = status.icon;
                    const category = categoryConfig[item.category];
                    const stockPercentage = (item.quantity / item.maxStock) * 100;

                    return (
                      <TableRow key={item.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <div 
                              className="w-10 h-10 rounded-lg flex items-center justify-center"
                              style={{ backgroundColor: `${category.color}20` }}
                            >
                              <Package className="w-5 h-5" style={{ color: category.color }} />
                            </div>
                            <div>
                              <p className="text-sm text-gray-900 dark:text-white">{item.name}</p>
                              <p className="text-xs text-gray-500">{item.unit}</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge 
                            style={{ 
                              backgroundColor: `${category.color}20`,
                              color: category.color,
                              borderColor: `${category.color}40`
                            }}
                          >
                            {category.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-sm text-gray-900 dark:text-white">
                                {item.quantity} / {item.maxStock}
                              </span>
                            </div>
                            <Progress value={stockPercentage} className="h-1.5 w-24" />
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {item.location}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Avatar className="w-6 h-6">
                              <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white text-xs">
                                {item.responsible.split(' ').slice(0, 2).map(n => n[0]).join('')}
                              </AvatarFallback>
                            </Avatar>
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              {item.responsible.split(' ')[item.responsible.split(' ').length - 1]}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={status.color}>
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {status.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {new Date(item.lastUpdate).toLocaleDateString('es-ES')}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openMovementDialog(item)}
                              title="Registrar movimiento"
                            >
                              <Archive className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEditDialog(item)}
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openDeleteDialog(item)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts">
          <div className="space-y-4">
            {inventory.filter(i => i.status === 'critical' || i.status === 'low').length === 0 ? (
              <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
                <CardContent className="p-12 text-center">
                  <CheckCircle className="w-16 h-16 text-[#4CAF50] mx-auto mb-4" />
                  <h3 className="text-gray-900 dark:text-white mb-2">¡Todo en orden!</h3>
                  <p className="text-gray-500 dark:text-gray-400">
                    No hay alertas críticas en el inventario
                  </p>
                </CardContent>
              </Card>
            ) : (
              inventory
                .filter(i => i.status === 'critical' || i.status === 'low')
                .sort((a, b) => a.status === 'critical' ? -1 : 1)
                .map((item) => {
                  const status = statusConfig[item.status];
                  const StatusIcon = status.icon;
                  const category = categoryConfig[item.category];

                  return (
                    <Card 
                      key={item.id} 
                      className={`border-2 ${
                        item.status === 'critical' 
                          ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10' 
                          : 'border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/10'
                      }`}
                    >
                      <CardContent className="p-6">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-4 flex-1">
                            <div 
                              className="w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0"
                              style={{ backgroundColor: `${category.color}20` }}
                            >
                              <StatusIcon className="w-6 h-6" style={{ color: category.color }} />
                            </div>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-2">
                                <h4 className="text-sm text-gray-900 dark:text-white">{item.name}</h4>
                                <Badge className={status.color}>{status.label}</Badge>
                              </div>
                              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                                Stock actual: <strong>{item.quantity} {item.unit}</strong> • 
                                Mínimo requerido: <strong>{item.minStock} {item.unit}</strong>
                              </p>
                              <div className="flex items-center gap-4 text-sm text-gray-500">
                                <span>📍 {item.location}</span>
                                <span>👤 {item.responsible}</span>
                              </div>
                            </div>
                          </div>
                          <Button
                            size="sm"
                            className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white"
                            onClick={() => openMovementDialog(item)}
                          >
                            Registrar Entrada
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  );
                })
            )}
          </div>
        </TabsContent>

        {/* Analytics Tab */}
        <TabsContent value="analytics" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Category Distribution */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Distribución por Categoría</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <ResponsiveContainer width="50%" height={200}>
                    <PieChart>
                      <Pie
                        data={categoryData}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                      >
                        {categoryData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="space-y-2 flex-1">
                    {categoryData.map((category) => (
                      <div key={category.name} className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full" 
                            style={{ backgroundColor: category.color }}
                          />
                          <span className="text-sm text-gray-700 dark:text-gray-300">{category.name}</span>
                        </div>
                        <span className="text-sm text-gray-900 dark:text-white">{category.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Stock Status */}
            <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
              <CardHeader>
                <CardTitle className="text-gray-900 dark:text-white">Estado de Stock</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={stockData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis dataKey="status" stroke="#666" />
                    <YAxis stroke="#666" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e0e0e0',
                        borderRadius: '8px'
                      }} 
                    />
                    <Bar dataKey="count" fill="#4CAF50" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Material</DialogTitle>
            <DialogDescription>
              Actualiza la información del material en el inventario
            </DialogDescription>
          </DialogHeader>
          <ItemForm onSubmit={handleEditItem} submitLabel="Guardar Cambios" />
        </DialogContent>
      </Dialog>

      {/* Movement Dialog */}
      <Dialog open={isMovementOpen} onOpenChange={setIsMovementOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Registrar Movimiento de Inventario</DialogTitle>
            <DialogDescription>
              {selectedItem?.name} - Stock actual: {selectedItem?.quantity} {selectedItem?.unit}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Tipo de Movimiento</Label>
              <Select
                value={movementData.type}
                onValueChange={(value) => setMovementData({ ...movementData, type: value as 'in' | 'out' })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="in">Entrada (Aumentar stock)</SelectItem>
                  <SelectItem value="out">Salida (Reducir stock)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Cantidad</Label>
              <Input
                type="number"
                min="1"
                value={movementData.quantity}
                onChange={(e) => setMovementData({ ...movementData, quantity: parseInt(e.target.value) || 0 })}
              />
            </div>

            <div className="space-y-2">
              <Label>Motivo</Label>
              <Textarea
                placeholder="Describe el motivo del movimiento..."
                value={movementData.reason}
                onChange={(e) => setMovementData({ ...movementData, reason: e.target.value })}
              />
            </div>

            <div className="bg-gray-50 dark:bg-gray-900 rounded-lg p-3">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                Stock resultante: <strong>
                  {movementData.type === 'in' 
                    ? (selectedItem?.quantity || 0) + movementData.quantity
                    : (selectedItem?.quantity || 0) - movementData.quantity
                  } {selectedItem?.unit}
                </strong>
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsMovementOpen(false)}>
              Cancelar
            </Button>
            <Button
              className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white"
              onClick={handleMovement}
              disabled={movementData.quantity <= 0 || !movementData.reason}
            >
              Registrar Movimiento
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Eliminar material del inventario?</AlertDialogTitle>
            <AlertDialogDescription>
              Estás a punto de eliminar <strong>{selectedItem?.name}</strong> del inventario.
              Esta acción no se puede deshacer.
              <br /><br />
              <strong>Recomendación ISO 25010:</strong> Considera marcar el material como archivado 
              en lugar de eliminarlo para mantener el historial de inventario.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteItem}
              className="bg-red-600 hover:bg-red-700"
            >
              Eliminar Material
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
