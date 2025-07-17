import React, { useState, useEffect } from "react";
import { Mail, Lock, Eye, EyeOff, User } from "lucide-react";

export default function LoginForm({ handleNavigation, axios}) {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  // Ocultar navbar y footer cuando se monta el componente
  useEffect(() => {
    // Ocultar elementos de navegación
    const navbar = document.querySelector('nav, .navbar, [class*="nav"]');
    const footer = document.querySelector('footer, .footer, [class*="footer"]');

    if (navbar) navbar.style.display = "none";
    if (footer) footer.style.display = "none";

    // Aplicar estilos al body
    document.body.style.margin = "0";
    document.body.style.padding = "0";
    document.body.style.overflow = "hidden";

    // Limpiar al desmontar
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
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setMessage("");

    try {
      const response = await axios.post("http://localhost:8080/api", {
        email: formData.email,
        password: formData.password,
      });

      setMessage("¡Inicio de sesión exitoso!");
      // Manejar respuesta exitosa
    } catch (error) {
      setMessage("Error al iniciar sesión. Inténtalo de nuevo.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Bootstrap CSS con namespace específico */}
      <link
        href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css"
        rel="stylesheet"
      />

      <div className="login-page-container">
        <div style={{ width: "100%", maxWidth: "400px" }}>
          <button
            type="button"
            onClick={() => handleNavigation("home")}
            style={{
              position: "absolute",
              top: "20px",
              left: "20px",
              background: "rgba(255, 255, 255, 0.9)",
              border: "1px solid #dee2e6",
              borderRadius: "50%",
              width: "45px",
              height: "45px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              transition: "all 0.3s ease",
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
              zIndex: "10",
            }}
            onMouseEnter={(e) => {
              e.target.style.background = "white";
              e.target.style.transform = "scale(1.05)";
            }}
            onMouseLeave={(e) => {
              e.target.style.background = "rgba(255, 255, 255, 0.9)";
              e.target.style.transform = "scale(1)";
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#333"
              strokeWidth="2"
            >
              <path d="M19 12H5M12 19l-7-7 7-7" />
            </svg>
          </button>
          {/* Header */}
          <div className="login-text-center login-mb-4">
            <div className="login-user-icon">
              <User size={40} color="white" />
            </div>
            <h1
              style={{
                fontSize: "1.5rem",
                fontWeight: "bold",
                color: "#333",
                marginBottom: "0.5rem",
              }}
            >
              CENTRO DE TERAPIAS
            </h1>
            <p
              style={{
                fontSize: "1.2rem",
                color: "#666",
                fontWeight: "500",
                margin: "0",
              }}
            >
              JUAN PABLO II
            </p>
            <p
              style={{ fontSize: "0.9rem", color: "#888", marginTop: "0.5rem" }}
            >
              Iniciar Sesión
            </p>
          </div>

          {/* Login Card */}
          <div className="login-card">
            <div className="login-p-4">
              <div>
                {/* Email Field */}
                <div className="login-mb-3">
                  <label className="login-form-label">Correo Electrónico</label>
                  <div className="login-input-group">
                    <Mail className="login-input-icon" size={20} />
                    <input
                      name="email"
                      type="email"
                      required
                      value={formData.email}
                      onChange={handleInputChange}
                      className="login-form-control"
                      placeholder="tu@email.com"
                    />
                  </div>
                </div>

                {/* Password Field */}
                <div className="login-mb-4">
                  <label className="login-form-label">Contraseña</label>
                  <div className="login-input-group">
                    <Lock className="login-input-icon" size={20} />
                    <input
                      name="password"
                      type={showPassword ? "text" : "password"}
                      required
                      value={formData.password}
                      onChange={handleInputChange}
                      className="login-form-control"
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="login-password-toggle"
                    >
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </button>
                  </div>
                </div>

                {/* Submit Button */}
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={loading}
                  className="login-btn"
                >
                  {loading ? (
                    <div className="login-d-flex login-align-items-center login-justify-content-center">
                      <div className="login-spinner"></div>
                      Iniciando sesión...
                    </div>
                  ) : (
                    "Iniciar Sesión"
                  )}
                </button>

                {/* Message */}
                {message && (
                  <div
                    className={
                      message.includes("exitoso")
                        ? "login-alert-success"
                        : "login-alert-danger"
                    }
                  >
                    {message}
                  </div>
                )}
              </div>

              {/* Footer Links */}
              <div className="login-text-center login-mt-3">
                <button className="login-link">
                  ¿Olvidaste tu contraseña?
                </button>
                <div
                  style={{
                    fontSize: "0.8rem",
                    color: "#666",
                    marginTop: "0.5rem",
                  }}
                >
                  ¿Necesitas ayuda?
                  <a
                    href="mailto:informes@centrojuanpabloii.com"
                    className="login-link"
                    style={{ marginLeft: "4px" }}
                  >
                    informes@centrojuanpabloii.com
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Text */}
          <div className="login-text-center login-mt-3">
            <small style={{ color: "#888" }}>
              Centro de Terapias Juan Pablo II © 2024
            </small>
          </div>
        </div>
      </div>
    </>
  );
}
