import React, { useState } from "react";
import emailjs from "@emailjs/browser";

const ContactContent = () => {
    const [formData, setFormData] = useState({
        name: "",
        email: "",
        subject: "",
        message: "",
    });

    const [message, setMessage] = useState("");
    const [errors, setErrors] = useState({});

    const handleInputChange = (e) => {
        setFormData({
            ...formData,
            [e.target.name]: e.target.value,
        });
    };

    const validate = () => {
        let tempErrors = {};
        if (!formData.name) tempErrors.name = "Por favor ingrese su nombre.";
        if (!formData.email) {
            tempErrors.email = "Por favor ingrese su correo.";
        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
            tempErrors.email = "Por favor ingrese un correo válido.";
        }
        if (!formData.subject) tempErrors.subject = "Por favor ingrese el sujeto.";
        if (!formData.message) tempErrors.message = "Por favor ingrese su mensaje.";
        setErrors(tempErrors);
        return Object.keys(tempErrors).length === 0;
    };

    const sendEmail = (e) => {
        e.preventDefault();

        if (!validate()) return;

        // Parámetros para el administrador
        const adminTemplateParams = {
            user_name: formData.name,
            user_email: formData.email,
            subject: formData.subject,
            message: formData.message,
            to_email: "informes@centrojuanpabloii.com",
        };

        // Parámetros para el usuario
        const userTemplateParams = {
            user_name: formData.name,
            user_email: formData.email,
            reply_to: "informes@centrojuanpabloii.com",
            message: "Gracias por contactarnos. Hemos recibido tu mensaje y lo revisaremos pronto.",
        };

        // Enviar correo al administrador
        emailjs
            .send(
                "service_olcgbip", // ID del servicio
                "template_trm57wu", // ID de la plantilla para el admin
                adminTemplateParams,
                "FOH1RobDyzI3oW_rY" // ID público del usuario
            )
            .then(
                (response) => {
                    console.log("Correo enviado al administrador", response.status, response.text);

                    // Enviar correo de respuesta al usuario
                    emailjs
                        .send(
                            "service_olcgbip", // ID del servicio
                            "template_wf1pe58", // ID de la plantilla para el usuario
                            userTemplateParams,
                            "FOH1RobDyzI3oW_rY"
                        )
                        .then(
                            (userResponse) => {
                                console.log("Correo enviado al usuario", userResponse.status, userResponse.text);
                                setMessage("¡Correo enviado con éxito! Pronto nos comunicaremos contigo.");
                                setFormData({ name: "", email: "", subject: "", message: "" });
                            },
                            (err) => {
                                console.error("Error al enviar correo al usuario", err);
                                setMessage("Hubo un error al enviar el correo de confirmación.");
                            }
                        );
                },
                (err) => {
                    console.error("Error al enviar correo al administrador", err);
                    setMessage("Hubo un error al enviar el correo. Inténtalo más tarde.");
                }
            );
    };

    return (
        <>
            <div className="container-fluid page-header" style={{ marginBottom: "90px" }}>
                <div className="container">
                    <div className="d-flex flex-column justify-content-center" style={{ minHeight: "300px" }}>
                        <h3 className="display-4 text-white text-uppercase">Contáctanos</h3>
                        <div className="d-inline-flex text-white">
                            <p className="m-0 text-uppercase"><a className="text-white" href="">Inicio</a></p>
                            <i className="fa fa-angle-double-right pt-1 px-3"></i>
                            <p className="m-0 text-uppercase">Contáctanos</p>
                        </div>
                    </div>
                </div>
            </div>
            <div className="row justify-content-center">
                <div className="col-lg-8">
                    <div className="contact-form bg-secondary rounded p-5">
                        <form onSubmit={sendEmail}>
                            <div className="control-group mb-3"> {/* Agregar margen inferior */}
                                <input
                                    type="text"
                                    className={`form-control border-0 p-4 ${errors.name ? "is-invalid" : ""}`}
                                    name="name"
                                    placeholder="Su nombre"
                                    value={formData.name}
                                    onChange={handleInputChange}
                                />
                                {errors.name && <p className="help-block text-danger">{errors.name}</p>}
                            </div>
                            <div className="control-group mb-3"> {/* Agregar margen inferior */}
                                <input
                                    type="email"
                                    className={`form-control border-0 p-4 ${errors.email ? "is-invalid" : ""}`}
                                    name="email"
                                    placeholder="Su correo electrónico"
                                    value={formData.email}
                                    onChange={handleInputChange}
                                />
                                {errors.email && <p className="help-block text-danger">{errors.email}</p>}
                            </div>
                            <div className="control-group mb-3"> {/* Agregar margen inferior */}
                                <input
                                    type="text"
                                    className={`form-control border-0 p-4 ${errors.subject ? "is-invalid" : ""}`}
                                    name="subject"
                                    placeholder="Sujeto"
                                    value={formData.subject}
                                    onChange={handleInputChange}
                                />
                                {errors.subject && <p className="help-block text-danger">{errors.subject}</p>}
                            </div>
                            <div className="control-group mb-3"> {/* Agregar margen inferior */}
                                <textarea
                                    className={`form-control border-0 py-3 px-4 ${errors.message ? "is-invalid" : ""}`}
                                    rows="5"
                                    name="message"
                                    placeholder="Mensaje"
                                    value={formData.message}
                                    onChange={handleInputChange}
                                ></textarea>
                                {errors.message && <p className="help-block text-danger">{errors.message}</p>}
                            </div>
                            <div className="text-center">
                                <button className="btn btn-primary py-3 px-5" type="submit">
                                    Enviar
                                </button>
                            </div>
                        </form>
                        {message && <p className="text-center mt-3">{message}</p>}
                    </div>
                </div>
            </div>
        </>
    );
};

export default ContactContent;