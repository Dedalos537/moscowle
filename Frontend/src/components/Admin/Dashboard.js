// src/components/Admin/Dashboard.js

import React, { useEffect, useState } from "react";
import axiosInstance from "../../utils/axiosConfig";

export default function AdminDashboard() {
  const [solicitudes, setSolicitudes] = useState([]);
  const [mensaje, setMensaje] = useState("");

  // Proteger el dashboard: solo admins autenticados pueden verlo
  useEffect(() => {
    const isAuth = localStorage.getItem("isAuthenticated");
    const rol = localStorage.getItem("rol");
    if (!isAuth || rol !== "ADMIN") {
      window.location.href = "/login";
    }
  }, []);

  const fetchSolicitudes = async () => {
    try {
      const res = await axiosInstance.get("/registro");
      setSolicitudes(Array.isArray(res.data) ? res.data : res.data.solicitudes || []);
    } catch (error) {
      setMensaje("Error al cargar solicitudes: " + (error.response?.data?.message || error.message)); // Mostrar error real
      console.error("Error al cargar solicitudes:", error);
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

  // Botón de cerrar sesión
  const handleLogout = async () => {
    try {
      await axiosInstance.post("/api/logout");
    } catch (e) {}
    localStorage.removeItem("isAuthenticated");
    localStorage.removeItem("rol");
    window.location.href = "/login";
  };

  return (
    <div className="container mt-5">
      <div className="d-flex justify-content-between align-items-center">
        <h2>Solicitudes de Registro</h2>
        <button className="btn btn-danger" onClick={handleLogout}>Cerrar sesión</button>
      </div>
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
