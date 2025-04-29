import React, { useState, useEffect } from 'react';
import './Modal.css';

const InfoModal = ({ isOpen, onRequestClose, selectedTerapia, handleNavigation, activeContent }) => {
  // Validación de props
  const onClose = typeof onRequestClose === 'function' ? onRequestClose : () => {};
  const [imageLoaded, setImageLoaded] = useState(false);
  const [imageVisible, setImageVisible] = useState(true);
  const [isMobileMenuOpen, setMobileMenuOpen] = useState(false);
  
  // Handler para el menú móvil
  const handleMenuToggle = () => {
    setMobileMenuOpen(!isMobileMenuOpen);
  };
  
  // Handler para los enlaces de navegación
  const handleLinkClick = (content) => {
    // Verificar si handleNavigation existe y es una función antes de llamarla
    if (typeof handleNavigation === 'function') {
      handleNavigation(content);
    } else {
      console.warn('handleNavigation prop is not provided or is not a function');
    }
    setMobileMenuOpen(false); // Cierra el menú al cambiar de pestaña
  };

  useEffect(() => {
    // Bloquea el deslizamiento de la página cuando el modal está abierto
    if (isOpen) {
      document.body.style.overflow = 'hidden'; // Bloquea el scroll
      setImageVisible(true); // Muestra la imagen al abrir el modal
      // No resetear imageLoaded aquí para evitar parpadeos
    } else {
      document.body.style.overflow = ''; // Restablece el scroll cuando el modal se cierra
    }

    // Limpieza al desmontar el componente
    return () => {
      document.body.style.overflow = ''; // Asegúrate de restaurar el scroll
    };
  }, [isOpen]);

  // Cierra el modal al hacer clic fuera del contenido
  const handleClickOutside = (e) => {
    if (e.target.classList.contains('modal-container')) {
      onClose();
    }
  };

  // Handlers para la imagen
  const handleImageLoad = () => {
    setImageLoaded(true);
  };

  const handleImageError = () => {
    setImageVisible(false); // Oculta la imagen si hay un error al cargar
  };

  // No renderizar nada si no hay terapia seleccionada o el modal está cerrado
  if (!selectedTerapia || !isOpen) return null;
  
  // Verificar si las propiedades necesarias existen en selectedTerapia
  const { title = 'Terapia', description = '', image = '' } = selectedTerapia;

  return (
    <div
      className={`modal-container ${isOpen ? 'show' : ''}`}
      onClick={handleClickOutside}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div
        className={`modal-content ${isOpen ? 'fade-in' : 'fade-out'}`}
        onClick={(e) => e.stopPropagation()}
        style={{ width: '600px', height: '400px', display: 'flex', flexDirection: 'column' }}
      >
        {/* Encabezado del modal */}
        <div className="modal-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px' }}>
          <h2 id="modal-title" style={{ color: '#4CAF50', margin: 0 }}>{title}</h2>
          <button 
            className="btn btn-close" 
            onClick={onClose} 
            style={{ background: 'none', border: 'none', cursor: 'pointer' }}
            aria-label="Cerrar"
          >
            <i className="fa fa-times fa-lg text-primary"></i>
          </button>
        </div>

        {/* Contenido principal del modal */}
        <div className="modal-body" style={{ display: 'flex', flex: 1 }}>
          {imageVisible && (
            <div className="modal-image-container" style={{ flex: 1 }}>
              <img
                src={image}
                alt={`Imagen ilustrativa de ${title}`}
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: '10px',
                  opacity: imageLoaded ? 1 : 0,
                  transition: 'opacity 0.5s ease-in-out'
                }}
                onLoad={handleImageLoad}
                onError={handleImageError}
              />
            </div>
          )}
          <div className="modal-description" style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
            <p style={{ maxHeight: '170px', overflowY: 'auto' }}>{description}</p>
          </div>
        </div>

        {/* Pie del modal */}
        <div className="modal-footer" style={{ padding: '20px', textAlign: 'center' }}>
          <button
            className={`nav-link btn btn-primary ${activeContent === "services" ? "active" : ""}`}
            onClick={() => {
              try {
                handleLinkClick("services");
                // Cierra el modal después de la navegación
                onClose();
              } catch (error) {
                console.error("Error en la navegación:", error);
                onClose();
              }
            }}
            style={{ border: 'none', background: '#4CAF50', color: 'white', padding: '10px 20px', borderRadius: '5px', cursor: 'pointer' }}
          >
            Saber Más
          </button>
        </div>
      </div>
    </div>
  );
};

export default InfoModal;