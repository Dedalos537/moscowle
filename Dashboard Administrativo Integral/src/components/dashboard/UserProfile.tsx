import { useState, useEffect } from 'react';
import { User, Mail, Lock, Eye, EyeOff, Save, Camera, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Label } from '../ui/label';
import { Avatar, AvatarFallback, AvatarImage } from '../ui/avatar';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { Alert, AlertDescription } from '../ui/alert';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';

interface UserProfileProps {
  onClose: () => void;
}

interface UserData {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  specialty?: string;
  avatar?: string;
  phone?: string;
  address?: string;
  createdAt?: string;
}

export function UserProfile({ onClose }: UserProfileProps) {
  const [userData, setUserData] = useState<UserData>({
    id: 1,
    firstName: 'Administrador',
    lastName: 'Principal',
    email: 'admin@juanpablo2.com',
    role: 'admin',
    specialty: 'Administración General',
    phone: '+51 921 507 470',
    address: 'Jr. Vicús 311, Piura, Perú'
  });

  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Estados para cambio de contraseña
  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });

  // Estados para edición de perfil
  const [editData, setEditData] = useState(userData);

  useEffect(() => {
    // Cargar datos del usuario desde localStorage
    const storedUserData = localStorage.getItem('user_data');
    if (storedUserData) {
      try {
        const user = JSON.parse(storedUserData);
        const formattedUserData: UserData = {
          id: user.id || 1,
          firstName: user.first_name || 'Administrador',
          lastName: user.last_name || 'Principal',
          email: user.email || 'admin@juanpablo2.com',
          role: user.role || 'admin',
          specialty: user.specialty || 'Administración General',
          phone: user.phone || '+51 921 507 470',
          address: user.address || 'Jr. Vicús 311, Piura, Perú',
          createdAt: user.created_at
        };
        setUserData(formattedUserData);
        setEditData(formattedUserData);
      } catch (error) {
        console.error('Error parsing user data:', error);
      }
    }
  }, []);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    setMessage(null);

    try {
      // Simular llamada a API
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Actualizar datos locales
      setUserData(editData);
      
      // Actualizar localStorage
      const currentUserData = JSON.parse(localStorage.getItem('user_data') || '{}');
      const updatedUserData = {
        ...currentUserData,
        first_name: editData.firstName,
        last_name: editData.lastName,
        email: editData.email,
        phone: editData.phone,
        address: editData.address
      };
      localStorage.setItem('user_data', JSON.stringify(updatedUserData));
      
      setMessage({ type: 'success', text: 'Perfil actualizado correctamente' });
      setIsEditing(false);
    } catch (error) {
      setMessage({ type: 'error', text: 'Error al actualizar el perfil' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setMessage({ type: 'error', text: 'Las contraseñas no coinciden' });
      return;
    }

    if (passwordData.newPassword.length < 8) {
      setMessage({ type: 'error', text: 'La nueva contraseña debe tener al menos 8 caracteres' });
      return;
    }

    setIsSaving(true);
    setMessage(null);

    try {
      const response = await fetch('http://127.0.0.1:8001/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        },
        body: JSON.stringify({
          current_password: passwordData.currentPassword,
          new_password: passwordData.newPassword
        }),
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Contraseña cambiada correctamente' });
        setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      } else {
        setMessage({ type: 'error', text: 'Error al cambiar la contraseña' });
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Error de conexión' });
    } finally {
      setIsSaving(false);
    }
  };

  const getInitials = () => {
    return `${userData.firstName?.charAt(0) || ''}${userData.lastName?.charAt(0) || ''}`.toUpperCase();
  };

  const getRoleLabel = () => {
    switch (userData.role) {
      case 'admin': return 'Administrador';
      case 'therapist': return 'Terapeuta';
      case 'receptionist': return 'Recepcionista';
      default: return userData.role;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Mi Perfil</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Gestiona tu información personal y configuración de cuenta
          </p>
        </div>
        <Button onClick={onClose} variant="outline">
          Cerrar
        </Button>
      </div>

      {/* Alert Messages */}
      {message && (
        <Alert className={message.type === 'success' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
          {message.type === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          ) : (
            <AlertCircle className="h-4 w-4 text-red-600" />
          )}
          <AlertDescription className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
            {message.text}
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="profile">Información Personal</TabsTrigger>
          <TabsTrigger value="security">Seguridad</TabsTrigger>
        </TabsList>

        {/* Perfil Tab */}
        <TabsContent value="profile" className="space-y-6">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Información Personal</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Avatar Section */}
              <div className="flex items-center gap-6">
                <div className="relative">
                  <Avatar className="w-24 h-24">
                    <AvatarImage src={userData.avatar} alt={`${userData.firstName} ${userData.lastName}`} />
                    <AvatarFallback className="bg-gradient-to-br from-[#4CAF50] to-[#2E7D32] text-white text-xl">
                      {getInitials()}
                    </AvatarFallback>
                  </Avatar>
                  <Button
                    size="icon"
                    variant="secondary"
                    className="absolute -bottom-2 -right-2 rounded-full w-8 h-8"
                    onClick={() => {}}
                  >
                    <Camera className="w-4 h-4" />
                  </Button>
                </div>
                <div className="flex-1">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                    {userData.firstName} {userData.lastName}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">{userData.email}</p>
                  <Badge className="mt-2 bg-[#4CAF50] text-white">
                    {getRoleLabel()}
                  </Badge>
                </div>
                <div className="flex gap-2">
                  {!isEditing ? (
                    <Button onClick={() => setIsEditing(true)} variant="outline">
                      <User className="w-4 h-4 mr-2" />
                      Editar Perfil
                    </Button>
                  ) : (
                    <>
                      <Button onClick={() => setIsEditing(false)} variant="outline">
                        Cancelar
                      </Button>
                      <Button onClick={handleSaveProfile} disabled={isSaving}>
                        <Save className="w-4 h-4 mr-2" />
                        {isSaving ? 'Guardando...' : 'Guardar'}
                      </Button>
                    </>
                  )}
                </div>
              </div>

              <Separator />

              {/* Form Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label htmlFor="firstName">Nombre</Label>
                  <Input
                    id="firstName"
                    value={isEditing ? editData.firstName : userData.firstName}
                    onChange={(e) => setEditData({ ...editData, firstName: e.target.value })}
                    disabled={!isEditing}
                    className="bg-gray-50 dark:bg-gray-900"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="lastName">Apellido</Label>
                  <Input
                    id="lastName"
                    value={isEditing ? editData.lastName : userData.lastName}
                    onChange={(e) => setEditData({ ...editData, lastName: e.target.value })}
                    disabled={!isEditing}
                    className="bg-gray-50 dark:bg-gray-900"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="email"
                      type="email"
                      value={isEditing ? editData.email : userData.email}
                      onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                      disabled={!isEditing}
                      className="pl-10 bg-gray-50 dark:bg-gray-900"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Teléfono</Label>
                  <Input
                    id="phone"
                    value={isEditing ? editData.phone || '' : userData.phone || ''}
                    onChange={(e) => setEditData({ ...editData, phone: e.target.value })}
                    disabled={!isEditing}
                    className="bg-gray-50 dark:bg-gray-900"
                    placeholder="+51 000 000 000"
                  />
                </div>

                <div className="space-y-2 md:col-span-2">
                  <Label htmlFor="address">Dirección</Label>
                  <Input
                    id="address"
                    value={isEditing ? editData.address || '' : userData.address || ''}
                    onChange={(e) => setEditData({ ...editData, address: e.target.value })}
                    disabled={!isEditing}
                    className="bg-gray-50 dark:bg-gray-900"
                    placeholder="Dirección completa"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="role">Rol</Label>
                  <Input
                    id="role"
                    value={getRoleLabel()}
                    disabled
                    className="bg-gray-100 dark:bg-gray-800"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="specialty">Especialidad</Label>
                  <Input
                    id="specialty"
                    value={userData.specialty || 'No especificada'}
                    disabled
                    className="bg-gray-100 dark:bg-gray-800"
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Security Tab */}
        <TabsContent value="security" className="space-y-6">
          <Card className="border-gray-200 dark:border-gray-800 bg-white dark:bg-[#1E1E2E]">
            <CardHeader>
              <CardTitle className="text-gray-900 dark:text-white">Cambiar Contraseña</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="currentPassword">Contraseña Actual</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="currentPassword"
                      type={showCurrentPassword ? "text" : "password"}
                      value={passwordData.currentPassword}
                      onChange={(e) => setPasswordData({ ...passwordData, currentPassword: e.target.value })}
                      className="pl-10 pr-10"
                      placeholder="Ingresa tu contraseña actual"
                    />
                    <button
                      type="button"
                      onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showCurrentPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="newPassword">Nueva Contraseña</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="newPassword"
                      type={showNewPassword ? "text" : "password"}
                      value={passwordData.newPassword}
                      onChange={(e) => setPasswordData({ ...passwordData, newPassword: e.target.value })}
                      className="pl-10 pr-10"
                      placeholder="Mínimo 8 caracteres"
                    />
                    <button
                      type="button"
                      onClick={() => setShowNewPassword(!showNewPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showNewPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="confirmPassword">Confirmar Nueva Contraseña</Label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      id="confirmPassword"
                      type={showConfirmPassword ? "text" : "password"}
                      value={passwordData.confirmPassword}
                      onChange={(e) => setPasswordData({ ...passwordData, confirmPassword: e.target.value })}
                      className="pl-10 pr-10"
                      placeholder="Repite la nueva contraseña"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="pt-4">
                  <Button 
                    onClick={handleChangePassword} 
                    disabled={isSaving || !passwordData.currentPassword || !passwordData.newPassword || !passwordData.confirmPassword}
                    className="w-full sm:w-auto"
                  >
                    <Lock className="w-4 h-4 mr-2" />
                    {isSaving ? 'Cambiando...' : 'Cambiar Contraseña'}
                  </Button>
                </div>
              </div>

              <Separator />

              <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900 dark:text-white">Información de Seguridad</h4>
                <div className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                  <p>• La contraseña debe tener al menos 8 caracteres</p>
                  <p>• Incluye mayúsculas, minúsculas y números</p>
                  <p>• Evita usar información personal</p>
                  <p>• Cambia tu contraseña regularmente</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}