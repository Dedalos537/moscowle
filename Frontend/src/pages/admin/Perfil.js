import React from 'react';

const Perfil = () => {
  // Simulación de datos (luego se pueden traer de la API o sesión)
  const admin = {
    nombre: 'Administrador Principal',
    correo: 'admin@moscowle.com',
    rol: 'Superadmin'
  };

  return (
    <div>
      <h2>👤 Perfil del Administrador</h2>
      <div className="card shadow-sm mt-4">
        <div className="card-body">
          <p><strong>Nombre:</strong> {admin.nombre}</p>
          <p><strong>Correo:</strong> {admin.correo}</p>
          <p><strong>Rol:</strong> {admin.rol}</p>

          <button className="btn btn-outline-secondary btn-sm me-2">Cambiar contraseña</button>
          <button className="btn btn-outline-danger btn-sm">Cerrar sesión</button>
        </div>
      </div>
    </div>
  );
};

export default Perfil;
