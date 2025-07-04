import React, { useState, useEffect } from "react";
import { Mail, Lock, Eye, EyeOff, User } from "lucide-react";
import axiosInstance from "../../utils/axiosConfig";
import './Login.css'; // Asegúrate de crear este archivo CSS

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
      // Guardar autenticación y rol
      localStorage.setItem("isAuthenticated", "true");
      localStorage.setItem("rol", rol);
      // Redirección según el rol usando window.location.href para recargar la app
      if (rol === "ADMIN") {
        window.location.href = "/dashboard";
      } else {
        window.location.href = "/";
      }
    } catch (err) {
      setMessage("Credenciales inválidas o sin autorización aún");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
    <style>
      
      
    </style>
    <div className="login-page-container">
      <div className="login-form-container">
        <div className="text-center mb-4">
          <User  size={40} color="white" />
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
    </>
  );
}
