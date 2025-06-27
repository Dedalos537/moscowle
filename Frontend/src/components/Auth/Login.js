// Paso 1: Crear la estructura para la autenticación y registro supervisado
// Archivo: src/components/Auth/Login.js
// Basado en los requisitos y bajo el estándar ISO 25010 (funcionalidad, usabilidad, seguridad...)

import React, { useState, useEffect } from "react";
import { Mail, Lock, Eye, EyeOff, User } from "lucide-react";
import axiosInstance from "../../utils/axiosConfig";

export default function Login({ handleNavigation }) {
  const [formData, setFormData] = useState({ email: "", password: "" });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const navbar = document.querySelector("nav, .navbar, [class*='nav']");
    const footer = document.querySelector("footer, .footer, [class*='footer']");

    if (navbar) navbar.style.display = "none";
    if (footer) footer.style.display = "none";

    document.body.style.margin = "0";
    document.body.style.padding = "0";
    document.body.style.overflow = "hidden";

    return () => {
      if (navbar) navbar.style.display = "";
      if (footer) footer.style.display = "";
      document.body.style.margin = "";
      document.body.style.padding = "";
      document.body.style.overflow = "";
    };
  }, []);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const res = await axiosInstance.post("/login", formData);
      const { rol } = res.data;
      setMessage("¡Inicio de sesión exitoso!");
      // Redirección según el rol
      if (rol === "ADMIN") {
        handleNavigation("dashboard");
      } else {
        handleNavigation("home");
      }
    } catch (err) {
      setMessage("Credenciales inválidas o sin autorización aún");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page-container">
      <div style={{ maxWidth: "400px", margin: "auto" }}>
        <div className="text-center mb-4">
          <User size={40} color="white" />
          <h1>CENTRO DE TERAPIAS</h1>
          <p>JUAN PABLO II</p>
          <p>Iniciar Sesión</p>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label>Correo Electrónico</label>
            <div className="input-group">
              <Mail size={20} />
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                className="form-control"
                required
              />
            </div>
          </div>
          <div className="mb-4">
            <label>Contraseña</label>
            <div className="input-group">
              <Lock size={20} />
              <input
                type={showPassword ? "text" : "password"}
                name="password"
                value={formData.password}
                onChange={handleInputChange}
                className="form-control"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="btn btn-outline-secondary"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>
          <button type="submit" className="btn btn-primary w-100" disabled={loading}>
            {loading ? "Iniciando..." : "Iniciar Sesión"}
          </button>
          {message && <div className="alert alert-info mt-3">{message}</div>}
        </form>
      </div>
    </div>
  );
}
