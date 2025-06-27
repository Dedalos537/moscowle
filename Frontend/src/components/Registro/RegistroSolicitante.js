

import React, { useState } from "react";
import axiosInstance from "../../utils/axiosConfig";

export default function RegistroSolicitante() {
  const [formData, setFormData] = useState({
    nombre: "",
    correo: "",
    servicio: ""
  });

  const [mensaje, setMensaje] = useState("");
  const [errores, setErrores] = useState({});

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
    <div className="col-lg-5">
      <div className="card border-0">
        <div className="card-header bg-light text-center p-4">
          <h1 className="m-0">Date a conocer!</h1>
        </div>
        <div className="card-body rounded-bottom bg-primary p-5">
          <form onSubmit={sendSolicitud}>
            <div className="form-group mb-3">
              <input
                type="text"
                name="nombre"
                className={`form-control border-0 p-4 ${errores.nombre ? "is-invalid" : ""}`}
                placeholder="Ingrese su nombre"
                value={formData.nombre}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group mb-3">
              <input
                type="email"
                name="correo"
                className={`form-control border-0 p-4 ${errores.correo ? "is-invalid" : ""}`}
                placeholder="Ingrese su correo"
                value={formData.correo}
                onChange={handleInputChange}
              />
            </div>

            <div className="form-group mb-4">
              <select
                name="servicio"
                className={`form-control border-0 p-4 ${errores.servicio ? "is-invalid" : ""}`}
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

            <button className="btn btn-dark btn-block border-0 py-3" type="submit">
              Enviar
            </button>
          </form>

          {mensaje && <p className="text-center mt-3 text-white">{mensaje}</p>}
        </div>
      </div>
    </div>
  );
}
