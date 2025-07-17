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
  
  // Verificar si estamos en un entorno de navegador
  const isBrowser = typeof window !== 'undefined';

  // Se utilizará para manejar la navegación a services de forma segura
  const navigateToServices = () => {
    try {
      // Comprobación segura de la función handleNavigation
      if (typeof handleNavigation === 'function') {
        handleNavigation("services");
        return true;
      } else {
        console.warn('handleNavigation no es una función');
        
        // Intentar navegar de otras formas si handleNavigation no existe
        if (isBrowser) {
          // Alternativa 1: Buscar elementos con ID
          const servicesSection = document.getElementById('services');
          if (servicesSection) {
            servicesSection.scrollIntoView({ behavior: 'smooth' });
            return true;
          }
          
          // Alternativa 2: Buscar enlaces con href services
          const servicesLinks = document.querySelectorAll('a[href*="services"]');
          if (servicesLinks.length > 0) {
            servicesLinks[0].click();
            return true;
          }
          
          // Alternativa 3: Si hay un hash en la URL
          window.location.hash = 'services';
          return true;
        }
      }
    } catch (error) {
      console.error("Error al navegar:", error);
    }
    
    return false;
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
                // Intenta navegar a services de forma segura
                const navigationSuccessful = navigateToServices();
                
                // Cierra el modal después de un breve retraso para permitir que la navegación ocurra
                setTimeout(() => {
                  onClose();
                }, navigationSuccessful ? 200 : 0);
                
                // Cierra el menú móvil si estaba abierto
                setMobileMenuOpen(false);
              } catch (error) {
                console.error("Error en el botón:", error);
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