// src/components/Admin/Dashboard.js

import React, { useEffect, useState } from "react";
import axiosInstance from "../../utils/axiosConfig";

export default function AdminDashboard() {
  const [solicitudes, setSolicitudes] = useState([]);
  const [mensaje, setMensaje] = useState("");

  const fetchSolicitudes = async () => {
    try {
      const res = await axiosInstance.get("/registro");
      setSolicitudes(res.data);
    } catch (error) {
      setMensaje("Error al cargar solicitudes");
    }
  };

  const aprobar = async (id) => {
    try {
      await axiosInstance.put(`/registro/${id}/aprobar`);
      setMensaje("Solicitud aprobada correctamente");
      fetchSolicitudes();
    } catch (error) {
      setMensaje("No se pudo aprobar la solicitud");
    }
  };

  useEffect(() => {
    fetchSolicitudes();
  }, []);

  return (
    <div className="container mt-5">
      <h2>Solicitudes de Registro</h2>
      {mensaje && <div className="alert alert-info">{mensaje}</div>}

      <table className="table table-bordered mt-3">
        <thead>
          <tr>
            <th>#</th>
            <th>Nombre</th>
            <th>Correo</th>
            <th>Servicio Solicitado</th>
            <th>Estado</th>
            <th>Acción</th>
          </tr>
        </thead>
        <tbody>
          {solicitudes.map((solicitud, index) => (
            <tr key={solicitud.id}>
              <td>{index + 1}</td>
              <td>{solicitud.nombre}</td>
              <td>{solicitud.correo}</td>
              <td>{solicitud.servicio}</td>
              <td>{solicitud.estado}</td>
              <td>
                {solicitud.estado === "PENDIENTE" && (
                  <button
                    className="btn btn-success btn-sm"
                    onClick={() => aprobar(solicitud.id)}
                  >
                    Aprobar
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
