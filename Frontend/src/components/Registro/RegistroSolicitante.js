import React, { useState } from "react";
import axiosInstance from "../../utils/axiosConfig";

export default function RegistroSolicitante() {
    const [formData, setFormData] = useState({
        nombre: "",
        correo: "",
        servicio: ""
    });

    const [mensaje, setMensaje] = useState("");
    const [errores, setErrores] = useState({}); // Corrected: useState({}) instead of {}

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const validar = () => {
        const err = {};
        if (!formData.nombre) err.nombre = true;
        if (!formData.correo) err.correo = true;
        if (!formData.servicio) err.servicio = true;
        setErrores(err);
        return Object.keys(err).length === 0;
    };

    const sendSolicitud = async (e) => {
        e.preventDefault();
        if (!validar()) return;

        try {
            await axiosInstance.post("/registro", formData);
            setMensaje("¡Solicitud enviada correctamente! Pronto será aprobada.");
            setFormData({ nombre: "", correo: "", servicio: "" });
            setErrores({});
        } catch (error) {
            setMensaje("Error al enviar la solicitud. Intenta nuevamente.");
        }
    };

    return (
        <>
            <style>{`
        .custom-card {
          box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
          border-radius: 20px;
          overflow: hidden;
          /* Adjusted for wider card */
          max-width: 700px; /* Increased max-width */
          width: 100%; /* Ensure it takes full available width up to max-width */
          margin: 0 auto;
          display: flex; /* Make it a flex container */
          flex-direction: row; /* Arrange header and form side-by-side */
        }

        .custom-header {
          background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
          position: relative;
          min-width: 250px; /* Give header a minimum width */
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 20px; /* Reduced padding */
          flex-shrink: 0; /* Prevent header from shrinking too much */
        }

        .custom-header::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="25" cy="25" r="1" fill="%23000" opacity="0.02"/><circle cx="75" cy="75" r="1" fill="%23000" opacity="0.02"/><circle cx="50" cy="10" r="1" fill="%23000" opacity="0.02"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
          z-index: 0; /* Ensure grain is behind content */
        }

        .custom-header > * {
            position: relative; /* Bring content above pseudo-element */
            z-index: 1;
        }

        .custom-icon {
          width: 50px; /* Slightly smaller icon */
          height: 50px;
          margin: 0 auto 15px; /* Reduced margin */
        }

        .custom-badge {
          background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
          color: white;
          padding: 6px 15px; /* Reduced padding */
          border-radius: 25px;
          font-size: 13px; /* Slightly smaller font */
          font-weight: 600;
          box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
          display: inline-block;
          margin-top: 10px; /* Reduced margin */
        }

       .custom-form-body {
          background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
          position: relative;
          z-index: 1;
          padding: 30px; /* Increased padding for form area */
          flex-grow: 1; /* Allow form body to take remaining space */
          display: flex;
          flex-direction: column;
          justify-content: center; /* Center content vertically */
        }

        .custom-form-body::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse"><circle cx="10" cy="10" r="1" fill="%23fff" opacity="0.1"/></pattern></defs><rect width="100" height="100" fill="url(%23dots)"/></svg>');
          z-index: 0;
          pointer-events: none;
        }

        .custom-form-body > * {
            position: relative; /* Bring content above pseudo-element */
            z-index: 1;
        }

        .custom-input {
         width: 100%;
         display: block;
         border: none !important;
         border-radius: 15px !important;
         padding: 12px 18px !important; /* Slightly reduced padding */
         font-size: 15px; /* Slightly smaller font */
         background: white;
         box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
         transition: all 0.3s ease;
        }

        .custom-input:focus {
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15), 0 0 0 3px rgba(255, 255, 255, 0.3) !important;
        transform: translateY(-2px);
        }

        .custom-input.is-invalid {
         border: 2px solid #dc3545 !important;
         box-shadow: 0 4px 15px rgba(220, 53, 69, 0.2);
        }

        .custom-btn {
          background: linear-gradient(135deg, #343a40 0%, #495057 100%) !important;
          border: none !important;
          border-radius: 15px !important;
          padding: 12px 25px !important; /* Slightly reduced padding */
          font-weight: 600;
          font-size: 15px; /* Slightly smaller font */
          box-shadow: 0 4px 15px rgba(52, 58, 64, 0.3);
          transition: all 0.3s ease;
          position: relative;
          overflow: hidden;
        }

        .custom-btn:hover {
          transform: translateY(-3px);
          box-shadow: 0 8px 25px rgba(52, 58, 64, 0.4);
        }

        .custom-btn:active {
          transform: translateY(-1px);
        }

        .custom-btn::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
          transition: left 0.5s;
        }

        .custom-btn:hover::before {
          left: 100%;
        }

        .feature-item {
          display: flex;
          align-items: center;
          margin-bottom: 6px; /* Reduced margin */
          font-size: 13px; /* Slightly smaller font */
          color: rgba(255, 255, 255, 0.9);
        }

        .feature-icon {
          width: 14px; /* Slightly smaller icon */
          height: 14px;
          margin-right: 8px; /* Reduced margin */
          background: rgba(255, 255, 255, 0.2);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .custom-alert {
          border: none;
          border-radius: 15px;
          padding: 12px 18px; /* Reduced padding */
          margin-top: 15px; /* Reduced margin */
          font-weight: 500;
          font-size: 14px; /* Slightly smaller font */
          background: rgba(255, 255, 255, 0.2);
          color: white;
          border: 1px solid rgba(255, 255, 255, 0.3);
        }

        .custom-alert.alert-success {
          background: rgba(255, 255, 255, 0.25);
        }

        .custom-alert.alert-danger {
          background: rgba(220, 53, 69, 0.2);
          border-color: rgba(220, 53, 69, 0.3);
        }

        @media (max-width: 991.98px) { /* Adjust breakpoint for larger screens (e.g., tablets in landscape) */
          .custom-card {
            flex-direction: column; /* Stack header and form vertically on smaller screens */
            max-width: 450px; /* Revert to original max-width for smaller screens */
          }
          .custom-header {
            min-width: unset; /* Remove min-width when stacked */
            padding: 30px; /* Revert header padding for stacked view */
          }
          .custom-icon {
            width: 60px; /* Revert icon size for stacked view */
            height: 60px;
            margin: 0 auto 20px;
          }
          .custom-badge {
            padding: 8px 20px;
            font-size: 14px;
            margin-top: 15px;
          }
          .custom-form-body {
            padding: 30px; /* Revert form body padding for stacked view */
          }
          .custom-input {
            padding: 15px 20px !important;
            font-size: 16px;
          }
          .custom-btn {
            padding: 15px 30px !important;
            font-size: 16px;
          }
          .feature-item {
            margin-bottom: 8px;
            font-size: 14px;
          }
          .feature-icon {
            width: 16px;
            height: 16px;
            margin-right: 10px;
          }
          .custom-alert {
            padding: 15px 20px;
            font-size: 14px;
            margin-top: 20px;
          }
        }

        @media (max-width: 767.98px) { /* Adjust breakpoint for medium/small screens */
          .custom-card {
            margin: 20px auto; /* Center card on very small screens */
            border-radius: 15px;
          }
        }

      `}</style>

            <div className="container-fluid py-5 px-3">
                <div className="row justify-content-center">
                    <div className="col-12">
                        <div className="custom-card">
                            {/* Header */}
                            <div className="custom-header text-center">
                                <div className="custom-icon">
                                    <svg width="24" height="24" fill="white" viewBox="0 0 24 24">
                                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                                    </svg>
                                </div>
                                <h1 className="h4 mb-2 font-weight-bold text-dark">¡Date a conocer!</h1>
                                <p className="text-muted mb-2" style={{ fontSize: '13px' }}>¿DESEAS INSCRIBIRTE?</p>
                                <div className="custom-badge">
                                    30% de descuento en la evaluación inicial
                                </div>
                            </div>

                            {/* Form Body */}
                            <div className="custom-form-body">
                                <div className="text-center mb-4">
                                    <p className="text-white mb-3" style={{ fontSize: '13px', lineHeight: '1.4' }}>
                                        Ingrese su nombre, dirección de correo electrónico y selecciona en qué deseas recibir
                                        información y nos contactaremos con usted
                                    </p>

                                    {/* Features */}
                                    <div className="text-left">
                                        <div className="feature-item">
                                            <div className="feature-icon">
                                                <svg width="8" height="8" fill="currentColor" viewBox="0 0 16 16">
                                                    <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z" />
                                                </svg>
                                            </div>
                                            Datos Seguros
                                        </div>
                                        <div className="feature-item">
                                            <div className="feature-icon">
                                                <svg width="8" height="8" fill="currentColor" viewBox="0 0 16 16">
                                                    <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z" />
                                                </svg>
                                            </div>
                                            Interacción personal y segura
                                        </div>
                                        <div className="feature-item">
                                            <div className="feature-icon">
                                                <svg width="8" height="8" fill="currentColor" viewBox="0 0 16 16">
                                                    <path d="M10.97 4.97a.235.235 0 0 0-.02.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.06L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-1.071-1.05z" />
                                                </svg>
                                            </div>
                                            Comunicación Directa
                                        </div>
                                    </div>
                                </div>

                                <form onSubmit={sendSolicitud}>
                                    <div className="form-group mb-3">
                                        <input
                                            type="text"
                                            name="nombre"
                                            className={`form-control custom-input ${errores.nombre ? "is-invalid" : ""}`}
                                            placeholder="Ingrese su nombre"
                                            value={formData.nombre}
                                            onChange={handleInputChange}
                                        />
                                    </div>

                                    <div className="form-group mb-3">
                                        <input
                                            type="email"
                                            name="correo"
                                            className={`form-control custom-input ${errores.correo ? "is-invalid" : ""}`}
                                            placeholder="Ingrese su correo electrónico"
                                            value={formData.correo}
                                            onChange={handleInputChange}
                                        />
                                    </div>

                                    <div className="form-group mb-4">
                                        <select
                                            name="servicio"
                                            className={`form-control custom-input ${errores.servicio ? "is-invalid" : ""}`}
                                            value={formData.servicio}
                                            onChange={handleInputChange}
                                        >
                                            <option value="">Seleccione un servicio</option>
                                            <option value="Terapias">Terapias</option>
                                            <option value="Terapias Integrales">Terapias Integrales</option>
                                            <option value="Material Virtual">Material Virtual</option>
                                            <option value="Material Físico">Material Físico</option>
                                        </select>
                                    </div>

                                    <button className="btn btn-block custom-btn w-100" type="submit">
                                        Enviar
                                    </button>
                                </form>

                                {mensaje && (
                                    <div className={`custom-alert ${mensaje.includes("Error") ? "alert-danger" : "alert-success"}`}>
                                        {mensaje}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}