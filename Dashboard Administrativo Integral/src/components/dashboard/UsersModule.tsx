import { useState, useEffect } from 'react';
import { Users, Plus, Search, Filter, Edit, Trash2, CheckCircle, XCircle, Shield, UserPlus, Mail, Phone, Calendar } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Avatar, AvatarFallback } from '../ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { getBackendUrl } from '../../utils/urlResolver';
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
import { Switch } from '../ui/switch';
import { Separator } from '../ui/separator';
import { ScrollArea } from '../ui/scroll-area';
import { toast } from 'sonner';

interface User {
  id: number;
  name: string;
  email: string;
  phone: string;
  role: 'admin' | 'therapist' | 'assistant';
  specialty?: string;
  status: 'active' | 'inactive';
  joinDate: string;
  patients?: number;
  sessions?: number;
}

const initialUsers: User[] = [
  {
    id: 1,
    name: 'Dra. Ana Pérez',
    email: 'ana.perez@juanpablo2.com',
    phone: '+52 555 1234 5678',
    role: 'therapist',
    specialty: 'Lenguaje',
    status: 'active',
    joinDate: '2023-01-15',
    patients: 24,
    sessions: 156
  },
  {
    id: 2,
    name: 'Lic. Roberto Díaz',
    email: 'roberto.diaz@juanpablo2.com',
    phone: '+52 555 2345 6789',
    role: 'therapist',
    specialty: 'Ocupacional',
    status: 'active',
    joinDate: '2023-03-20',
    patients: 18,
    sessions: 124
  },
  {
    id: 3,
    name: 'Dr. Juan López',
    email: 'juan.lopez@juanpablo2.com',
    phone: '+52 555 3456 7890',
    role: 'therapist',
    specialty: 'Física',
    status: 'active',
    joinDate: '2022-11-10',
    patients: 28,
    sessions: 198
  },
  {
    id: 4,
    name: 'Dra. Laura Méndez',
    email: 'laura.mendez@juanpablo2.com',
    phone: '+52 555 4567 8901',
    role: 'therapist',
    specialty: 'Psicológica',
    status: 'active',
    joinDate: '2023-05-08',
    patients: 16,
    sessions: 102
  },
  {
    id: 5,
    name: 'María García',
    email: 'maria.garcia@juanpablo2.com',
    phone: '+52 555 5678 9012',
    role: 'assistant',
    status: 'active',
    joinDate: '2024-01-12',
  },
  {
    id: 6,
    name: 'Dr. Administrador Principal',
    email: 'admin@juanpablo2.com',
    phone: '+52 555 0000 0000',
    role: 'admin',
    status: 'active',
    joinDate: '2022-01-01',
  },
];

const roleConfig = {
  admin: { label: 'Administrador', color: 'bg-purple-100 text-purple-700 border-purple-200', icon: Shield },
  therapist: { label: 'Terapeuta', color: 'bg-blue-100 text-blue-700 border-blue-200', icon: UserPlus },
  assistant: { label: 'Asistente', color: 'bg-gray-100 text-gray-700 border-gray-200', icon: Users },
};

export function UsersModule() {
  const [users, setUsers] = useState<User[]>([]);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [filterRole, setFilterRole] = useState('all');
  const [searchTerm, setSearchTerm] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    phone: '',
    role: 'therapist' as User['role'],
    specialty: '',
    status: 'active' as User['status'],
  });
  const [roles, setRoles] = useState<Array<{ id: number; name: string }>>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState<string | null>(null);
  
  useEffect(() => {
    let mounted = true;
    setRolesLoading(true);
    setRolesError(null);

    const BACKEND = getBackendUrl((import.meta as any)?.env?.VITE_BACKEND_URL);
    const url = `${BACKEND.replace(/\/$/, '')}/api/roles`;

    fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.message || body?.error || 'Error cargando roles');
        }
        return res.json();
      })
      .then((data) => {
        if (!mounted) return;
        setRoles(Array.isArray(data?.roles) ? data.roles : []);
      })
      .catch((err: any) => {
        if (!mounted) return;
        setRolesError(err?.message || String(err));
      })
      .finally(() => {
        if (!mounted) return;
        setRolesLoading(false);
      });

    return () => { mounted = false; };
  }, []);

  // Load users from backend (use initialUsers as fallback on error)
  useEffect(() => {
    let mounted = true;
    setUsersLoading(true);
    setUsersError(null);

    const BACKEND = getBackendUrl((import.meta as any)?.env?.VITE_BACKEND_URL);
    const url = `${BACKEND.replace(/\/$/, '')}/api/users`;

    fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.message || body?.error || 'Error cargando usuarios');
        }
        return res.json();
      })
      .then((data) => {
        if (!mounted) return;
        // Expecting { users: [...] } or an array directly
        const list = Array.isArray(data?.users) ? data.users : (Array.isArray(data) ? data : []);
        if (list.length === 0) {
          // fallback to local sample data if backend returns empty
          setUsers(initialUsers);
        } else {
          // Map backend shape to local User type if necessary
          const mapped = list.map((u: any, idx: number) => ({
            id: u.id ?? idx + 1,
            name: u.name ?? u.full_name ?? u.email,
            email: u.email ?? '',
            phone: u.phone ?? u.telefono ?? '',
            role: (u.role_name || u.role || 'therapist') as User['role'],
            specialty: u.specialty ?? u.especialidad,
            status: (u.status || 'active') as User['status'],
            joinDate: u.created_at ? u.created_at.split('T')[0] : (u.joinDate ?? new Date().toISOString().split('T')[0]),
            patients: typeof u.patients === 'number' ? u.patients : undefined,
            sessions: typeof u.sessions === 'number' ? u.sessions : undefined,
          }));
          setUsers(mapped);
        }
      })
      .catch((err: any) => {
        if (!mounted) return;
        setUsersError(err?.message || String(err));
        // fallback to local mock data so UI remains usable
        setUsers(initialUsers);
      })
      .finally(() => {
        if (!mounted) return;
        setUsersLoading(false);
      });

    return () => { mounted = false; };
  }, []);
  const [isCreating, setIsCreating] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [createdPassword, setCreatedPassword] = useState<string | null>(null);
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  const handleCreateUser = () => {
    // Call backend register endpoint as admin
    setIsCreating(true);
    setServerError(null);

    const BACKEND = getBackendUrl((import.meta as any)?.env?.VITE_BACKEND_URL);
    const url = `${BACKEND.replace(/\/$/, '')}/api/auth/register`;

    // send role name to backend; backend will map to role_id

    // generate a temporary password for initial login (will be emailed by server if implemented)
    const tempPassword = Math.random().toString(36).slice(-10) + 'A1!';

    const token = (() => {
      try {
        return localStorage.getItem('auth_token') || '';
      } catch (e) {
        return '';
      }
    })();

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ email: formData.email, password: tempPassword, role: formData.role }),
    })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}));
        if (!res.ok) {
          const msg = body?.msg || (body?.message || 'Error al crear usuario');
          throw new Error(msg || 'Error al crear usuario');
        }

        const created = body.user;
        const newUser: User = {
          id: created.id || users.length + 1,
          name: formData.name,
          email: created.email,
          phone: formData.phone,
          role: formData.role as User['role'],
          specialty: formData.specialty || undefined,
          status: formData.status as User['status'],
          joinDate: created.created_at ? created.created_at.split('T')[0] : new Date().toISOString().split('T')[0],
          patients: formData.role === 'therapist' ? 0 : undefined,
          sessions: formData.role === 'therapist' ? 0 : undefined,
        };

        setUsers((u) => [...u, newUser]);
        toast.success(`${roleConfig[formData.role].label} creado exitosamente`);
        // show generated password to admin so they can copy it or send it to the user
        setCreatedPassword(tempPassword);
        setShowPasswordModal(true);
        setIsCreateOpen(false);
        resetForm();
      })
      .catch((err: Error) => {
        setServerError(err.message);
        toast.error(err.message || 'Error del servidor');
      })
      .finally(() => setIsCreating(false));
  };

  const handleEditUser = () => {
    if (!selectedUser) return;

    setUsers(users.map(user => 
      user.id === selectedUser.id 
        ? { ...user, ...formData }
        : user
    ));

    toast.success('Usuario actualizado exitosamente');
    setIsEditOpen(false);
    setSelectedUser(null);
    resetForm();
  };

  const handleDeleteUser = () => {
    if (!selectedUser) return;

    setUsers(users.filter(user => user.id !== selectedUser.id));
    toast.success('Usuario eliminado exitosamente');
    setDeleteDialogOpen(false);
    setSelectedUser(null);
  };

  const handleToggleStatus = (userId: number) => {
    setUsers(users.map(user =>
      user.id === userId
        ? { ...user, status: user.status === 'active' ? 'inactive' : 'active' }
        : user
    ));
    toast.success('Estado actualizado');
  };

  const openEditDialog = (user: User) => {
    setSelectedUser(user);
    setFormData({
      name: user.name,
      email: user.email,
      phone: user.phone,
      role: user.role,
      specialty: user.specialty || '',
      status: user.status,
    });
    setIsEditOpen(true);
  };

  const openDeleteDialog = (user: User) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
  };

  const resetForm = () => {
    setFormData({
      name: '',
      email: '',
      phone: '',
      role: 'therapist',
      specialty: '',
      status: 'active',
    });
  };

  const filteredUsers = users.filter(user => {
    const matchesRole = filterRole === 'all' || user.role === filterRole;
    const matchesSearch = user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         user.email.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesRole && matchesSearch;
  });

  const UserForm = ({ onSubmit, submitLabel }: { onSubmit: () => void; submitLabel: string }) => (
    <ScrollArea className="max-h-[500px] pr-4">
      <div className="space-y-4 py-4">
        {serverError && (
          <div className="mb-4 text-sm text-red-700 bg-red-50 p-2 rounded">
            {serverError}
          </div>
        )}
        <div className="space-y-2">
          <Label>Nombre Completo *</Label>
          <Input
            placeholder="Ej: Dra. María González"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <Label>Correo Electrónico *</Label>
          <Input
            type="email"
            placeholder="correo@juanpablo2.com"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <Label>Teléfono *</Label>
          <Input
            placeholder="+52 555 0000 0000"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
          />
        </div>

        <div className="space-y-2">
          <Label>Rol *</Label>
          <Select
            value={formData.role}
            onValueChange={(value: string) => setFormData({ ...formData, role: value as User['role'] })}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {rolesLoading && <SelectItem value="loading" disabled>Cargando roles...</SelectItem>}
              {!rolesLoading && roles.length > 0 && roles.map((r) => (
                <SelectItem key={r.id} value={r.name}>
                  { (roleConfig as any)[r.name]?.label ?? r.name }
                </SelectItem>
              ))}
              {!rolesLoading && roles.length === 0 && (
                <>
                  <SelectItem value="therapist">Terapeuta</SelectItem>
                  <SelectItem value="assistant">Asistente</SelectItem>
                  <SelectItem value="admin">Administrador</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>

        {formData.role === 'therapist' && (
          <div className="space-y-2">
            <Label>Especialidad *</Label>
            <Select
              value={formData.specialty}
              onValueChange={(value: string) => setFormData({ ...formData, specialty: value })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar especialidad" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Lenguaje">Lenguaje</SelectItem>
                <SelectItem value="Ocupacional">Ocupacional</SelectItem>
                <SelectItem value="Física">Física</SelectItem>
                <SelectItem value="Psicológica">Psicológica</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        <Separator />

        <div className="flex items-center justify-between">
          <div>
            <Label>Estado</Label>
            <p className="text-xs text-gray-500 mt-1">
              {formData.status === 'active' ? 'Usuario activo' : 'Usuario inactivo'}
            </p>
          </div>
          <Switch
            checked={formData.status === 'active'}
            onCheckedChange={(checked: boolean) => 
              setFormData({ ...formData, status: checked ? 'active' : 'inactive' })
            }
          />
        </div>

        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
          <p className="text-sm text-blue-700 dark:text-blue-300">
            <strong>Nota ISO 25010:</strong> Se enviará un correo automático con las credenciales de acceso 
            al usuario. La contraseña inicial deberá ser cambiada en el primer inicio de sesión (Seguridad).
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
          disabled={!formData.name || !formData.email || !formData.phone || 
                   (formData.role === 'therapist' && !formData.specialty) || isCreating}
        >
          {isCreating ? 'Creando...' : submitLabel}
        </Button>
      </DialogFooter>
    </ScrollArea>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-gray-900 dark:text-white">Gestión de Usuarios</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Administra terapeutas, asistentes y permisos del sistema
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="bg-gradient-to-r from-[#4CAF50] to-[#2E7D32] text-white">
              <Plus className="w-4 h-4 mr-2" />
              Crear Usuario
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Crear Nuevo Usuario</DialogTitle>
              <DialogDescription>
                Complete los datos del usuario. Los campos marcados con * son obligatorios.
              </DialogDescription>
            </DialogHeader>
                <UserForm onSubmit={handleCreateUser} submitLabel="Crear Usuario" />
          </DialogContent>
        </Dialog>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Total Usuarios</p>
              <Users className="w-5 h-5 text-[#4CAF50]" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">{users.length}</h3>
            <p className="text-xs text-gray-500">{users.filter(u => u.status === 'active').length} activos</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Terapeutas</p>
              <UserPlus className="w-5 h-5 text-blue-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">
              {users.filter(u => u.role === 'therapist').length}
            </h3>
            <p className="text-xs text-green-600">4 especialidades</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Asistentes</p>
              <Users className="w-5 h-5 text-gray-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">
              {users.filter(u => u.role === 'assistant').length}
            </h3>
            <p className="text-xs text-gray-500">Soporte operativo</p>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">Administradores</p>
              <Shield className="w-5 h-5 text-purple-500" />
            </div>
            <h3 className="text-gray-900 dark:text-white mb-1">
              {users.filter(u => u.role === 'admin').length}
            </h3>
            <p className="text-xs text-gray-500">Acceso completo</p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content */}
      <Tabs defaultValue="all" className="space-y-6">
        <div className="flex items-center justify-between">
          <TabsList className="bg-gray-100 dark:bg-gray-800">
            <TabsTrigger value="all" onClick={() => setFilterRole('all')}>
              Todos ({users.length})
            </TabsTrigger>
            <TabsTrigger value="therapists" onClick={() => setFilterRole('therapist')}>
              Terapeutas ({users.filter(u => u.role === 'therapist').length})
            </TabsTrigger>
            <TabsTrigger value="staff" onClick={() => setFilterRole('assistant')}>
              Asistentes ({users.filter(u => u.role === 'assistant').length})
            </TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Buscar usuarios..."
                className="pl-10 w-64"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>
        </div>

        <TabsContent value="all" className="space-y-4">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Usuario</TableHead>
                    <TableHead>Contacto</TableHead>
                    <TableHead>Rol</TableHead>
                    <TableHead>Especialidad</TableHead>
                    <TableHead>Estado</TableHead>
                    <TableHead>Pacientes</TableHead>
                    <TableHead>Fecha Ingreso</TableHead>
                    <TableHead className="text-right">Acciones</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredUsers.map((user) => {
                    const roleInfo = roleConfig[user.role];
                    const RoleIcon = roleInfo.icon;

                    return (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Avatar className="w-10 h-10">
                              <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                                {user.name.split(' ').slice(0, 2).map(n => n[0]).join('')}
                              </AvatarFallback>
                            </Avatar>
                            <div>
                              <p className="text-sm text-gray-900 dark:text-white">{user.name}</p>
                              <p className="text-xs text-gray-500">{user.email}</p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                            <Phone className="w-3 h-3" />
                            {user.phone}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={roleInfo.color}>
                            <RoleIcon className="w-3 h-3 mr-1" />
                            {roleInfo.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {user.specialty || '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Switch
                              checked={user.status === 'active'}
                              onCheckedChange={() => handleToggleStatus(user.id)}
                            />
                            <span className="text-sm text-gray-600 dark:text-gray-400">
                              {user.status === 'active' ? 'Activo' : 'Inactivo'}
                            </span>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {user.patients || '-'}
                        </TableCell>
                        <TableCell className="text-sm text-gray-600 dark:text-gray-400">
                          {new Date(user.joinDate).toLocaleDateString('es-ES')}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEditDialog(user)}
                            >
                              <Edit className="w-4 h-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openDeleteDialog(user)}
                              className="text-red-600 hover:text-red-700 hover:bg-red-50"
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

        <TabsContent value="therapists">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredUsers.filter(u => u.role === 'therapist').map((therapist) => (
              <Card key={therapist.id} className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <Avatar className="w-12 h-12">
                        <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white">
                          {therapist.name.split(' ').slice(0, 2).map(n => n[0]).join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <h4 className="text-sm text-gray-900 dark:text-white">{therapist.name}</h4>
                        <Badge variant="outline" className="mt-1">{therapist.specialty}</Badge>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEditDialog(therapist)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <Mail className="w-4 h-4" />
                      {therapist.email}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <Phone className="w-4 h-4" />
                      {therapist.phone}
                    </div>
                    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                      <Calendar className="w-4 h-4" />
                      Desde {new Date(therapist.joinDate).toLocaleDateString('es-ES')}
                    </div>
                  </div>

                  <Separator className="my-4" />

                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center">
                      <p className="text-2xl text-gray-900 dark:text-white">{therapist.patients}</p>
                      <p className="text-xs text-gray-500">Pacientes</p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl text-gray-900 dark:text-white">{therapist.sessions}</p>
                      <p className="text-xs text-gray-500">Sesiones</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="staff">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardContent className="p-6">
              <div className="space-y-4">
                {filteredUsers.filter(u => u.role === 'assistant').map((assistant) => (
                  <div
                    key={assistant.id}
                    className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700"
                  >
                    <div className="flex items-center gap-4">
                      <Avatar className="w-12 h-12">
                        <AvatarFallback className="bg-gradient-to-br from-gray-400 to-gray-600 text-white">
                          {assistant.name.split(' ').map(n => n[0]).join('')}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <h4 className="text-sm text-gray-900 dark:text-white">{assistant.name}</h4>
                        <p className="text-sm text-gray-500">{assistant.email}</p>
                        <Badge className="mt-1 bg-gray-100 text-gray-700">Asistente</Badge>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => openEditDialog(assistant)}>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openDeleteDialog(assistant)}
                        className="text-red-600"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Editar Usuario</DialogTitle>
            <DialogDescription>
              Actualiza la información del usuario seleccionado
            </DialogDescription>
          </DialogHeader>
          <UserForm onSubmit={handleEditUser} submitLabel="Guardar Cambios" />
        </DialogContent>
      </Dialog>

      {/* Created password modal */}
      <Dialog open={showPasswordModal} onOpenChange={setShowPasswordModal}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Credenciales creadas</DialogTitle>
            <DialogDescription>
              Se generó una contraseña temporal para el usuario. Copia y comparte con el usuario o envíala por correo.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4 space-y-3">
            <div className="text-sm">
              <strong>Correo:</strong> {formData.email}
            </div>
            <div className="text-sm">
              <strong>Contraseña temporal:</strong>
              <div className="mt-2 flex items-center gap-2">
                <code className="bg-gray-100 px-3 py-1 rounded">{createdPassword}</code>
                <Button
                  size="sm"
                  onClick={() => {
                    try {
                      navigator.clipboard.writeText(createdPassword || '');
                      toast.success('Contraseña copiada al portapapeles');
                    } catch (e) {
                      toast('No fue posible copiar');
                    }
                  }}
                >
                  Copiar
                </Button>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowPasswordModal(false)}>Cerrar</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Estás seguro?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción eliminará permanentemente al usuario <strong>{selectedUser?.name}</strong> del sistema.
              Esta acción no se puede deshacer.
              <br /><br />
              <strong>Nota ISO 25010:</strong> Se recomienda desactivar el usuario en lugar de eliminarlo
              para mantener la trazabilidad de registros históricos (Mantenibilidad).
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteUser}
              className="bg-red-600 hover:bg-red-700"
            >
              Eliminar Usuario
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
