import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Contactos = () => {
  const [mensajes, setMensajes] = useState([]);
  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState('');

  useEffect(() => {
    axios.get('/api/contactanos/listar')
      .then(res => setMensajes(res.data))
      .catch(err => console.error('Error al cargar contactos:', err));
  }, []);

  const filtrarMensajes = () => {
    return mensajes.filter(m =>
      m.nombre?.toLowerCase().includes(busqueda.toLowerCase()) ||
      m.correo?.toLowerCase().includes(busqueda.toLowerCase())
    ).filter(m => {
      if (!filtro) return true;
      return m.fecha?.startsWith(filtro);
    });
  };

  return (
    <div className="container-fluid">
      <div className="card shadow-sm">
        <div className="card-body">
          <h3 className="card-title mb-4">
            <i className="bi bi-envelope-paper me-2"></i> Gestión de Contactos
          </h3>

          <div className="row g-3 mb-4">
            <div className="col-md-6 col-lg-4">
              <input
                type="text"
                className="form-control"
                placeholder="Buscar por nombre o correo"
                value={busqueda}
                onChange={e => setBusqueda(e.target.value)}
              />
            </div>
            <div className="col-md-6 col-lg-3">
              <input
                type="date"
                className="form-control"
                value={filtro}
                onChange={e => setFiltro(e.target.value)}
              />
            </div>
          </div>

          <div className="table-responsive">
            <table className="table table-striped table-hover align-middle">
              <thead className="table-dark">
                <tr>
                  <th>Nombre</th>
                  <th>Correo</th>
                  <th>Fecha</th>
                  <th>Asunto</th>
                  <th>Mensaje</th>
                </tr>
              </thead>
              <tbody>
                {filtrarMensajes().map((m, i) => (
                  <tr key={i}>
                    <td>{m.nombre}</td>
                    <td>{m.correo}</td>
                    <td>{m.fecha}</td>
                    <td>{m.sujeto}</td>
                    <td>{m.mensaje}</td>
                  </tr>
                ))}
                {filtrarMensajes().length === 0 && (
                  <tr>
                    <td colSpan="5" className="text-center text-muted">
                      <i className="bi bi-info-circle me-2"></i> No hay resultados
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

        </div>
      </div>
    </div>
  );
};

export default Contactos;
