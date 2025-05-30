import React, { useEffect } from 'react';
import { Link, Outlet } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './admin.css';

const AdminLayout = () => {

  useEffect(() => {
    const botonScroll = document.querySelector('.scroll-to-top');
    if (botonScroll) {
      botonScroll.style.display = 'none';
    }

    // Limpieza opcional al salir
    return () => {
      if (botonScroll) {
        botonScroll.style.display = 'block';
      }
    };
  }, []);

  return (
    <div className="admin-container">
      {/* Sidebar */}
      <aside className="admin-sidebar">
        <h5 className="text-center mb-4">🛠️ Panel Admin</h5>
        <nav className="nav flex-column">
          <Link to="/admin/contactos" className="nav-link mb-2">
            <i className="bi bi-envelope-fill me-2"></i> Contactos
          </Link>
          <Link to="/admin/usuarios" className="nav-link mb-2">
            <i className="bi bi-people-fill me-2"></i> Usuarios
          </Link>
        </nav>
      </aside>

      {/* Main content */}
      <main className="admin-content">
        <header className="admin-header">
          <span>👤 Admin</span>
          <Link to="/admin/perfil" className="btn btn-outline-primary btn-sm me-2">Perfil</Link>
          <button className="btn btn-outline-danger btn-sm">Cerrar sesión</button>
        </header>

        <div className="admin-card">
          <Outlet />
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
