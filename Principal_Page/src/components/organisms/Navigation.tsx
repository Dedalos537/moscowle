import React, { useState } from "react";
import { motion } from "motion/react";
import { Moon, Sun, Menu, X, LogIn, Mail, Lock, Eye, EyeOff } from "lucide-react";
import { Button } from "../ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "../ui/dialog";
import { Alert, AlertDescription } from "../ui/alert";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { getBackendUrl, getDashboardUrl } from "../../utils/urlResolver";


interface NavigationProps {
  darkMode: boolean;
  toggleDarkMode: () => void;
  isLoggedIn: boolean;
  onLogin: () => void;
  onLogout?: () => void;
}

export function Navigation({ darkMode, toggleDarkMode, isLoggedIn, onLogin, onLogout }: NavigationProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);

  const navLinks = [
    { name: "Inicio", href: "#inicio" },
    { name: "Servicios", href: "#servicios" },
    { name: "Acerca", href: "#acerca" },
    { name: "Contacto", href: "#contacto" },
  ];

  const handleGoToDashboard = () => {
    const DASHBOARD_URL = getDashboardUrl((import.meta as any)?.env?.VITE_DASHBOARD_URL);
    window.location.href = DASHBOARD_URL;
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setLoginError(null);

    try {
      const BACKEND = getBackendUrl((import.meta as any)?.env?.VITE_BACKEND_URL);
      const loginUrl = `${BACKEND.replace(/\/$/, '')}/api/auth/login`;
      
      const payload = { email, password };
      console.log('[Navigation] Attempting login:', { url: loginUrl, payload });

      const response = await fetch(loginUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      console.log('[Navigation] Login response:', { status: response.status, ok: response.ok });

      if (!response.ok) {
        // try to parse error body
        let errMsg = 'Credenciales inválidas';
        try {
          const errJson = await response.json();
          errMsg = errJson.msg || errJson.detail || errJson.message || errMsg;
        } catch (e) { }
        throw new Error(errMsg);
      }

      const data = await response.json();
      const token = data.access_token;

      // Mostrar verificación explícita con el endpoint /auth/me
      setIsVerifying(true);
      try {
        const meUrl = BACKEND ? `${BACKEND.replace(/\/$/, '')}/api/auth/me` : '/api/auth/me';
        const meResp = await fetch(meUrl, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
        });

        if (!meResp.ok) {
          let errMsg = 'Error al verificar credenciales';
          try {
            const errJson = await meResp.json();
            errMsg = errJson.msg || errJson.detail || errJson.message || errMsg;
          } catch (e) { }
          throw new Error(errMsg);
        }

        const meData = await meResp.json();

        console.log('[Navigation] meData received:', meData);
        console.log('[Navigation] meData.is_admin:', meData?.is_admin);

        // Guardar token y usuario sólo si la verificación fue exitosa
        localStorage.setItem('auth_token', token);
        localStorage.setItem('user_data', JSON.stringify(meData));

        // Cerrar diálogo y avisar al contenedor
        setLoginOpen(false);
        onLogin();

        // Redirigir a la URL de moscowle
        const REDIRECT_URL = "https://moscowle.centrojuanpabloii.com";

        // Sólo redirigir si el usuario es admin
        const isAdmin = meData?.is_admin === true;
        const shouldRedirect = isAdmin;

        console.log('[Navigation] isAdmin:', isAdmin, 'shouldRedirect:', shouldRedirect);

        if (shouldRedirect) {
          // Debug: log redirect target + admin status to help diagnose redirect issues
          try {
            // eslint-disable-next-line no-console
            console.debug('[Navigation] redirect target:', REDIRECT_URL, 'isAdmin:', isAdmin, 'meData:', meData);
          } catch (e) {}
          
          // Guardar en localStorage antes de redirigir
          localStorage.setItem('auth_token', token);
          localStorage.setItem('user_data', JSON.stringify(meData));
          
          // También pasar como parámetros de URL como respaldo
          const params = new URLSearchParams({
            token: token,
            user: JSON.stringify(meData)
          });
          const redirectUrlWithParams = `${REDIRECT_URL}?${params.toString()}`;
          
          console.log('[Navigation] Final redirect URL:', redirectUrlWithParams);
          
          setIsRedirecting(true);
          
          // Esperar un momento para asegurar que localStorage se sincronize
          setTimeout(() => {
            try {
              window.location.assign(redirectUrlWithParams);
            } catch (e) {
              window.location.href = redirectUrlWithParams;
            }
          }, 100);
        }

      } finally {
        setIsVerifying(false);
      }

    } catch (error) {
      const message = error instanceof Error ? error.message : 'Error de conexión';
      setLoginError(message);
      // Aquí podrías mostrar un mensaje de error al usuario
    } finally {
      setIsLoading(false);
    }
  };

  const handleLogout = () => {
    // Limpiar token y datos
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_data');
    // Avisar al padre si existe
    if (onLogout) onLogout();
    // Redirigir a la página principal para mostrar estado no autenticado
    try {
      window.location.assign('/');
    } catch (e) {
      window.location.href = '/';
    }
  };

  const scrollToTop = () => {
    window.scrollTo({
      top: 0,
      behavior: "smooth",
    });
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
              onClick={scrollToTop}
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
              <Button
                variant="default"
                size="sm"
                className="gap-2 bg-primary hover:bg-primary/90"
                onClick={() => window.location.href = "https://moscowle.centrojuanpabloii.com"}
              >
                <LogIn className="w-4 h-4" />
                <span className="hidden lg:inline">Iniciar Sesión</span>
              </Button>
            )}
            {isLoggedIn && (
              <>
                <Button 
                  variant="default" 
                  size="sm" 
                  className="gap-2 bg-primary hover:bg-primary/90"
                  onClick={handleGoToDashboard}
                >
                  Dashboard
                </Button>
                <Button variant="ghost" size="sm" className="ml-2" onClick={handleLogout}>
                  Cerrar sesión
                </Button>
              </>
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
              <Button
                variant="default"
                size="icon"
                className="rounded-full bg-primary hover:bg-primary/90"
                onClick={() => window.location.href = "https://moscowle.centrojuanpabloii.com"}
              >
                <LogIn className="w-4 h-4" />
              </Button>
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
            {isLoggedIn && (
              <>
                <Button 
                  variant="default" 
                  size="sm"
                  className="w-full gap-2 bg-primary hover:bg-primary/90 mt-2 mx-4"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    handleGoToDashboard();
                  }}
                >
                  Dashboard
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="w-full mt-2 mx-4"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    handleLogout();
                  }}
                >
                  Cerrar sesión
                </Button>
              </>
            )}
          </motion.div>
        )}
      </div>
    </motion.nav>
  );
}
