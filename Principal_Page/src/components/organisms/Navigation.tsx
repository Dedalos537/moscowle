import { useState } from "react";
import { motion } from "motion/react";
import { Moon, Sun, Menu, X, LogIn, Mail, Lock, Eye, EyeOff } from "lucide-react";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Alert, AlertDescription } from "../ui/alert";
import { Input } from "../ui/input";
import { Label } from "../ui/label";

interface NavigationProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
  isLoggedIn: boolean;
  onLogin: () => void;
}

export function Navigation({ darkMode, toggleDarkMode, isLoggedIn, onLogin }: NavigationProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);

  const navLinks = [
    { name: "Inicio", href: "#inicio" },
    { name: "Servicios", href: "#servicios" },
    { name: "Acerca", href: "#acerca" },
    { name: "Contacto", href: "#contacto" },
  ];

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setLoginError(null);

    try {
      const response = await fetch('/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        // try to parse error body
        let errMsg = 'Credenciales inválidas';
        try {
          const errJson = await response.json();
          errMsg = errJson.detail || errJson.message || errMsg;
        } catch (e) {}
        throw new Error(errMsg);
      }

      const data = await response.json();
      localStorage.setItem('auth_token', data.access_token);
      localStorage.setItem('user_data', JSON.stringify(data.user));

      // Cerrar diálogo y avisar al contenedor
      setLoginOpen(false);
      onLogin();

      // Determinar URL del dashboard (prefiere env var si existe, sino localhost:3001)
  // Prefer Vite env var VITE_DASHBOARD_URL, else build a URL using the current hostname + port 3001
  // Usar variable de entorno si está disponible; fallback explícito a localhost:3001
  const DASHBOARD_URL = ((import.meta as any)?.env?.VITE_DASHBOARD_URL as string) || 'http://localhost:3001';

      // Sólo redirigir si el usuario es admin (si la respuesta incluye role)
      const rawRole = (data.user && (data.user.role || data.user.role_name)) || null;
      const role = rawRole ? String(rawRole).toLowerCase().trim() : null;
      const shouldRedirect = !role || role === 'admin' || role.includes('admin') || role === 'administrador';

      if (shouldRedirect) {
        // Marcar estado para mostrar el aviso y forzar redirección inmediatamente.
        setIsRedirecting(true);
        try {
          // Redirigir de forma inmediata para evitar que re-renderizaciones oculten el flujo
          window.location.assign(DASHBOARD_URL);
        } catch (e) {
          // Fallback
          window.location.href = DASHBOARD_URL;
        }
      }
      
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error de conexión';
      setLoginError(message);
      // Aquí podrías mostrar un mensaje de error al usuario
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <motion.nav
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ duration: 0.6 }}
      className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md bg-background/80 border-b border-border/50 shadow-sm"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <motion.div
            whileHover={{ scale: 1.05 }}
            className="flex items-center gap-3"
          >
            <img 
              src="/logo.svg" 
              alt="Centro de Terapias Juan Pablo II" 
              className="h-12 w-auto"
            />
            <div className="flex flex-col">
              <span className="font-semibold text-primary">Centro de Terapias</span>
              <span className="text-xs text-muted-foreground">Juan Pablo II</span>
            </div>
          </motion.div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center gap-4">
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                className="text-foreground/80 hover:text-primary transition-colors duration-300 relative group px-2"
              >
                {link.name}
                <span className="absolute bottom-0 left-0 w-0 h-0.5 bg-primary group-hover:w-full transition-all duration-300" />
              </a>
            ))}
            
            {!isLoggedIn && (
              <Dialog open={loginOpen} onOpenChange={setLoginOpen}>
                <DialogTrigger asChild>
                  <Button variant="default" size="sm" className="gap-2 bg-primary hover:bg-primary/90">
                    <LogIn className="w-4 h-4" />
                    <span className="hidden lg:inline">Iniciar Sesión</span>
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <Lock className="w-5 h-5 text-primary" />
                      </div>
                      Iniciar Sesión
                    </DialogTitle>
                    <DialogDescription>
                      Accede a tu cuenta del Centro de Terapias Juan Pablo II
                    </DialogDescription>
                  </DialogHeader>
                  {loginError && (
                    <Alert className="mb-4 border-red-200 bg-red-50">
                      <AlertDescription className="text-red-700">{loginError}</AlertDescription>
                    </Alert>
                  )}
                  {isRedirecting && (
                    <Alert className="mb-4 border-blue-200 bg-blue-50">
                      <AlertDescription className="text-blue-700">Redirigiendo al dashboard...</AlertDescription>
                    </Alert>
                  )}
                  <form onSubmit={handleLogin} className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label htmlFor="email">Correo Electrónico</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          id="email"
                          type="email"
                          placeholder="tu@email.com"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="pl-10"
                          required
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="password">Contraseña</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          id="password"
                          type={showPassword ? "text" : "password"}
                          placeholder="••••••••"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="pl-10 pr-10"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                      {isLoading ? "Iniciando sesión..." : "Iniciar Sesión"}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            )}
            
            <Button
              onClick={toggleDarkMode}
              variant="outline"
              size="icon"
              className="rounded-full"
            >
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </Button>
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center gap-2">
            {!isLoggedIn && (
              <Dialog open={loginOpen} onOpenChange={setLoginOpen}>
                <DialogTrigger asChild>
                  <Button variant="default" size="icon" className="rounded-full bg-primary hover:bg-primary/90">
                    <LogIn className="w-4 h-4" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="sm:max-w-md">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <Lock className="w-5 h-5 text-primary" />
                      </div>
                      Iniciar Sesión
                    </DialogTitle>
                    <DialogDescription>
                      Accede a tu cuenta del Centro de Terapias Juan Pablo II
                    </DialogDescription>
                  </DialogHeader>
                  {loginError && (
                    <Alert className="mb-4 border-red-200 bg-red-50">
                      <AlertDescription className="text-red-700">{loginError}</AlertDescription>
                    </Alert>
                  )}
                  {isRedirecting && (
                    <Alert className="mb-4 border-blue-200 bg-blue-50">
                      <AlertDescription className="text-blue-700">Redirigiendo al dashboard...</AlertDescription>
                    </Alert>
                  )}
                  <form onSubmit={handleLogin} className="space-y-4 mt-4">
                    <div className="space-y-2">
                      <Label htmlFor="email-mobile">Correo Electrónico</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          id="email-mobile"
                          type="email"
                          placeholder="tu@email.com"
                          value={email}
                          onChange={(e) => setEmail(e.target.value)}
                          className="pl-10"
                          required
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="password-mobile">Contraseña</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                          id="password-mobile"
                          type={showPassword ? "text" : "password"}
                          placeholder="••••••••"
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="pl-10 pr-10"
                          required
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        >
                          {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                        </button>
                      </div>
                    </div>
                    <Button type="submit" className="w-full" disabled={isLoading}>
                      {isLoading ? "Iniciando sesión..." : "Iniciar Sesión"}
                    </Button>
                  </form>
                </DialogContent>
              </Dialog>
            )}
            
            <Button
              onClick={toggleDarkMode}
              variant="outline"
              size="icon"
              className="rounded-full"
            >
              {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </Button>
            
            <Button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              variant="outline"
              size="icon"
              className="rounded-full"
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden py-4 border-t border-border/50"
          >
            {navLinks.map((link) => (
              <a
                key={link.name}
                href={link.href}
                onClick={() => setMobileMenuOpen(false)}
                className="block py-3 text-foreground/80 hover:text-primary hover:bg-primary/5 px-4 rounded-lg transition-all duration-300"
              >
                {link.name}
              </a>
            ))}
          </motion.div>
        )}
      </div>
    </motion.nav>
  );
}
