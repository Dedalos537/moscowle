import React, { useState } from "react";
import { contactanosAPI, manejarError } from '../../utils/axiosConfig';

const ContactContent = () => {
    const [formData, setFormData] = useState({
        nombre: "",
        correo: "",
        sujeto: "",
        mensaje: "",
    });

    const [message, setMessage] = useState("");
    const [messageType, setMessageType] = useState(""); // 'success' o 'error'
    const [errors, setErrors] = useState({});
    const [isLoading, setIsLoading] = useState(false);

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData({
            ...formData,
            [name]: value,
        });
        
        // Limpiar error específico cuando el usuario empiece a escribir
        if (errors[name]) {
            setErrors({
                ...errors,
                [name]: ""
            });
        }
    };

    const validateForm = () => {
        let tempErrors = {};
        
        if (!formData.nombre.trim()) {
            tempErrors.nombre = "Por favor ingrese su nombre.";
        } else if (formData.nombre.length > 100) {
            tempErrors.nombre = "El nombre no puede exceder 100 caracteres.";
        }
        
        if (!formData.correo.trim()) {
            tempErrors.correo = "Por favor ingrese su correo.";
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.correo)) {
            tempErrors.correo = "Por favor ingrese un correo válido.";
        } else if (formData.correo.length > 100) {
            tempErrors.correo = "El correo no puede exceder 100 caracteres.";
        }
        
        if (!formData.sujeto.trim()) {
            tempErrors.sujeto = "Por favor ingrese el sujeto.";
        } else if (formData.sujeto.length > 200) {
            tempErrors.sujeto = "El sujeto no puede exceder 200 caracteres.";
        }
        
        if (!formData.mensaje.trim()) {
            tempErrors.mensaje = "Por favor ingrese su mensaje.";
        } else if (formData.mensaje.length > 5000) {
            tempErrors.mensaje = "El mensaje no puede exceder 5000 caracteres.";
        }
        
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        // Limpiar mensajes anteriores
        setMessage("");
        setMessageType("");
        
        if (!validateForm()) {
            return;
        }
        
        setIsLoading(true);
        
        try {
            // Preparar datos para enviar
            const dataToSend = {
                nombre: formData.nombre.trim(),
                correo: formData.correo.trim().toLowerCase(),
                sujeto: formData.sujeto.trim(),
                mensaje: formData.mensaje.trim()
            };
            
            // Enviar datos usando la instancia configurada de Axios
            const response = await contactanosAPI.enviarMensaje(dataToSend);
            
            if (response.data.success) {
                setMessage(response.data.message);
                setMessageType("success");
                
                // Limpiar formulario
                setFormData({
                    nombre: "",
                    correo: "",
                    sujeto: "",
                    mensaje: ""
                });
                
                console.log("Mensaje guardado con ID:", response.data.id);
            } else {
                setMessage(response.data.message || "Error desconocido");
                setMessageType("error");
                
                // Manejar errores específicos de campos
                if (response.data.errors) {
                    setErrors(response.data.errors);
                }
            }
            
        } catch (error) {
            console.error("Error al enviar mensaje:", error);
            
            // Usar la función de manejo de errores centralizada
            const errorMessage = manejarError(error);
            setMessage(errorMessage);
            setMessageType("error");
            
            // Manejar errores de validación del backend
            if (error.response?.data?.errors) {
                setErrors(error.response.data.errors);
            }
            
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <>
            <div className="container-fluid page-header" style={{ marginBottom: "90px" }}>
                <div className="container">
                    <div className="d-flex flex-column justify-content-center" style={{ minHeight: "300px" }}>
                        <h3 className="display-4 text-white text-uppercase">Contáctanos</h3>
                        <div className="d-inline-flex text-white">
                            <p className="m-0 text-uppercase">
                                <a className="text-white" href="/">Inicio</a>
                            </p>
                            <i className="fa fa-angle-double-right pt-1 px-3"></i>
                            <p className="m-0 text-uppercase">Contáctanos</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <div className="row justify-content-center">
                <div className="col-lg-8">
                    <div className="contact-form bg-secondary rounded p-5">
                        <form onSubmit={handleSubmit}>
                            <div className="control-group mb-3">
                                <input
                                    type="text"
                                    className={`form-control border-0 p-4 ${errors.nombre ? "is-invalid" : ""}`}
                                    name="nombre"
                                    placeholder="Su nombre *"
                                    value={formData.nombre}
                                    onChange={handleInputChange}
                                    maxLength="100"
                                    disabled={isLoading}
                                />
                                {errors.nombre && (
                                    <div className="invalid-feedback d-block">
                                        {errors.nombre}
                                    </div>
                                )}
                            </div>
                            
                            <div className="control-group mb-3">
                                <input
                                    type="email"
                                    className={`form-control border-0 p-4 ${errors.correo ? "is-invalid" : ""}`}
                                    name="correo"
                                    placeholder="Su correo electrónico *"
                                    value={formData.correo}
                                    onChange={handleInputChange}
                                    maxLength="100"
                                    disabled={isLoading}
                                />
                                {errors.correo && (
                                    <div className="invalid-feedback d-block">
                                        {errors.correo}
                                    </div>
                                )}
                            </div>
                            
                            <div className="control-group mb-3">
                                <input
                                    type="text"
                                    className={`form-control border-0 p-4 ${errors.sujeto ? "is-invalid" : ""}`}
                                    name="sujeto"
                                    placeholder="Sujeto *"
                                    value={formData.sujeto}
                                    onChange={handleInputChange}
                                    maxLength="200"
                                    disabled={isLoading}
                                />
                                {errors.sujeto && (
                                    <div className="invalid-feedback d-block">
                                        {errors.sujeto}
                                    </div>
                                )}
                            </div>
                            
                            <div className="control-group mb-3">
                                <textarea
                                    className={`form-control border-0 py-3 px-4 ${errors.mensaje ? "is-invalid" : ""}`}
                                    rows="5"
                                    name="mensaje"
                                    placeholder="Mensaje *"
                                    value={formData.mensaje}
                                    onChange={handleInputChange}
                                    maxLength="5000"
                                    disabled={isLoading}
                                />
                                {errors.mensaje && (
                                    <div className="invalid-feedback d-block">
                                        {errors.mensaje}
                                    </div>
                                )}
                                <small className="text-muted">
                                    {formData.mensaje.length}/5000 caracteres
                                </small>
                            </div>
                            
                            <div className="text-center">
                                <button 
                                    className="btn btn-primary py-3 px-5" 
                                    type="submit"
                                    disabled={isLoading}
                                >
                                    {isLoading ? (
                                        <>
                                            <span className="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
                                            Enviando...
                                        </>
                                    ) : (
                                        "Enviar Mensaje"
                                    )}
                                </button>
                            </div>
                        </form>
                        
                        {message && (
                            <div className={`alert mt-4 ${messageType === 'success' ? 'alert-success' : 'alert-danger'}`} role="alert">
                                <div className="d-flex align-items-center">
                                    {messageType === 'success' ? (
                                        <i className="fa fa-check-circle me-2"></i>
                                    ) : (
                                        <i className="fa fa-exclamation-triangle me-2"></i>
                                    )}
                                    {message}
                                </div>
                            </div>
                        )}
                        
                        <div className="mt-4">
                            <small className="text-muted">
                                * Campos obligatorios
                                <br />
                                <strong>Nota:</strong> Asegúrate de que el servidor backend esté funcionando en el puerto correcto.
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
};

export default ContactContent;