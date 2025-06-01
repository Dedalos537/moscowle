import React, { useEffect, useState } from 'react';
import axios from 'axios';

const Usuarios = () => {
  const [usuarios, setUsuarios] = useState([]);
  const [roles, setRoles] = useState([]);
  const [nuevoUsuario, setNuevoUsuario] = useState({ correo: '', contrasena: '', rol: '' });
  const [editando, setEditando] = useState(null);

  useEffect(() => {
    cargarUsuarios();
    cargarRoles();
  }, []);

  const cargarUsuarios = () => {
    axios.get('/api/usuarios/listar')
      .then(res => setUsuarios(res.data))
      .catch(err => console.error('Error al cargar usuarios:', err));
  };

  const cargarRoles = () => {
    axios.get('/api/roles/listar')
      .then(res => {
        if (Array.isArray(res.data)) {
          setRoles(res.data);
        } else {
          console.error('Formato inesperado en respuesta de roles:', res.data);
          setRoles([]);
        }
      })
      .catch(err => {
        console.error('Error al cargar roles:', err);
        setRoles([]);
      });
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setNuevoUsuario(prev => ({ ...prev, [name]: value }));
  };

  const guardarUsuario = () => {
    const url = editando ? `/api/usuarios/${editando.id}` : '/api/usuarios';
    const metodo = editando ? axios.put : axios.post;

    const payload = {
      correo: nuevoUsuario.correo,
      contrasena: nuevoUsuario.contrasena,
      rol: { id: parseInt(nuevoUsuario.rol) }
    };

    metodo(url, payload)
      .then(() => {
        setNuevoUsuario({ correo: '', contrasena: '', rol: '' });
        setEditando(null);
        cargarUsuarios();
      })
      .catch(err => alert('Error al guardar usuario'));
  };

  const eliminarUsuario = (id) => {
    if (window.confirm("¿Eliminar este usuario?")) {
      axios.delete(`/api/usuarios/${id}`)
        .then(() => cargarUsuarios());
    }
  };

  const editarUsuario = (usuario) => {
    setEditando(usuario);
    setNuevoUsuario({
      correo: usuario.correo,
      contrasena: '',
      rol: usuario.rol?.id || ''
    });
  };

  return (
    <div className="container-fluid">
      <div className="card shadow-sm">
        <div className="card-body">
          <h3 className="card-title mb-4">
            <i className="bi bi-people-fill me-2"></i> Gestión de Usuarios
          </h3>

          <div className="row g-3 align-items-center mb-4">
            <div className="col-md-4">
              <input
                type="email"
                name="correo"
                placeholder="Correo"
                value={nuevoUsuario.correo}
                onChange={handleChange}
                className="form-control"
              />
            </div>
            <div className="col-md-3">
              <input
                type="password"
                name="contrasena"
                placeholder="Contraseña"
                value={nuevoUsuario.contrasena}
                onChange={handleChange}
                className="form-control"
              />
            </div>
            <div className="col-md-3">
              <select
                name="rol"
                value={nuevoUsuario.rol}
                onChange={handleChange}
                className="form-control"
              >
                <option value="">Seleccione un rol</option>
                {roles.map(rol => (
                  <option key={rol.id} value={rol.id}>
                    {rol.nombre}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-md-2 d-grid">
              <button onClick={guardarUsuario} className="btn btn-success">
                {editando ? 'Actualizar' : 'Agregar'} Usuario
              </button>
            </div>
          </div>

          <div className="table-responsive">
            <table className="table table-striped table-hover align-middle">
              <thead className="table-dark">
                <tr>
                  <th>Correo</th>
                  <th>Rol</th>
                  <th style={{ width: '150px' }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {usuarios.map((u) => (
                  <tr key={u.id}>
                    <td>{u.correo}</td>
                    <td>{u.rol?.nombre}</td>
                    <td>
                      <button onClick={() => editarUsuario(u)} className="btn btn-warning btn-sm me-2">
                        <i className="bi bi-pencil-square"></i>
                      </button>
                      <button onClick={() => eliminarUsuario(u.id)} className="btn btn-danger btn-sm">
                        <i className="bi bi-trash3"></i>
                      </button>
                    </td>
                  </tr>
                ))}
                {usuarios.length === 0 && (
                  <tr>
                    <td colSpan="3" className="text-center text-muted">
                      <i className="bi bi-info-circle me-2"></i> No hay usuarios registrados.
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

export default Usuarios;
