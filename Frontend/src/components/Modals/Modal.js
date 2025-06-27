import React, { useState, useEffect, useRef, useCallback } from "react";
import PropTypes from "prop-types";
import "./Modal.css";

/**
 * Modal component que cumple con estándares ISO 25010
 * @param {Object} props - Props del componente
 * @param {boolean} props.isOpen - Estado de apertura del modal
 * @param {Function} props.toggleModal - Función para abrir/cerrar modal
 * @param {string} props.title - Título del modal
 * @param {string} props.message - Mensaje principal
 * @param {string} props.whatsappUrl - URL de WhatsApp
 * @param {string} props.buttonText - Texto del botón de acción
 * @param {Function} props.onError - Callback para manejo de errores
 * @param {string} props.loadingText - Texto mostrado durante carga
 */
function Modal({ 
  isOpen, 
  toggleModal, 
  title = "Conectando...",
  message = "Nos pondremos en contacto a través de WhatsApp si le da click al botón de ir a WhatsApp.",
  whatsappUrl = "https://api.whatsapp.com/send/?phone=51995092832&text=Me+gustar%C3%ADa+mayor+informaci%C3%B3n+sobre+la+terapia+de+conducta&type=phone_number&app_absent=0",
  buttonText = "Ir a WhatsApp",
  onError = null,
  loadingText = "Cargando..."
}) {
  const modalRef = useRef(null);
  const previousActiveElement = useRef(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Manejo de errores interno
  const handleError = useCallback((errorMessage, errorObject = null) => {
    setError(errorMessage);
    if (onError && typeof onError === 'function') {
      onError(errorMessage, errorObject);
    }
    console.error('Modal Error:', errorMessage, errorObject);
  }, [onError]);

  // Gestión del scroll del body
  useEffect(() => {
    if (isOpen) {
      // Guardar elemento activo antes de abrir modal
      previousActiveElement.current = document.activeElement;
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
      // Restaurar foco al elemento anterior
      if (previousActiveElement.current && previousActiveElement.current.focus) {
        previousActiveElement.current.focus();
      }
    }

    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // Manejo de tecla Escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        toggleModal();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, toggleModal]);

  // Gestión de foco para accesibilidad
  useEffect(() => {
    if (isOpen && modalRef.current) {
      // Encontrar elementos focusables
      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      
      if (focusableElements.length > 0) {
        // Enfocar el primer elemento focusable (botón de cerrar)
        focusableElements[0].focus();
      }

      // Trap focus dentro del modal
      const handleTabKey = (e) => {
        if (e.key === 'Tab') {
          const firstElement = focusableElements[0];
          const lastElement = focusableElements[focusableElements.length - 1];

          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault();
            lastElement.focus();
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault();
            firstElement.focus();
          }
        }
      };

      modalRef.current.addEventListener('keydown', handleTabKey);

      return () => {
        if (modalRef.current) {
          modalRef.current.removeEventListener('keydown', handleTabKey);
        }
      };
    }
  }, [isOpen]);

  // Manejo de clic fuera del modal
  const handleClickOutside = useCallback((e) => {
    if (e.target.classList.contains("modal-container")) {
      toggleModal();
    }
  }, [toggleModal]);

  // Manejo del botón de WhatsApp con validación
  const handleWhatsAppClick = useCallback(async (e) => {
    try {
      setIsLoading(true);
      setError(null);

      // Validar URL
      if (!whatsappUrl || typeof whatsappUrl !== 'string') {
        throw new Error('URL de WhatsApp inválida');
      }

      // Validar que sea una URL de WhatsApp
      const whatsappDomains = ['api.whatsapp.com', 'wa.me', 'web.whatsapp.com'];
      const url = new URL(whatsappUrl);
      
      if (!whatsappDomains.some(domain => url.hostname.includes(domain))) {
        throw new Error('URL debe ser de WhatsApp');
      }

      // Simular delay de red para UX
      await new Promise(resolve => setTimeout(resolve, 500));

      // El navegador manejará la apertura del enlace
      // No hay nada más que hacer aquí ya que el href se encarga de todo

    } catch (error) {
      e.preventDefault(); // Prevenir navegación si hay error
      handleError('Error al intentar abrir WhatsApp. Intente nuevamente.', error);
    } finally {
      setIsLoading(false);
    }
  }, [whatsappUrl, handleError]);

  // No renderizar si no está abierto
  if (!isOpen) {
    return null;
  }

  return (
    <div
      className={`modal-container ${isOpen ? "show" : ""}`}
      onClick={handleClickOutside}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      aria-describedby="modal-description"
      ref={modalRef}
    >
      <div 
        className="modal-content" 
        onClick={(e) => e.stopPropagation()}
        role="document"
      >
        <div className="modal-header">
          <h5 
            id="modal-title" 
            className="modal-title"
          >
            {title}
          </h5>
          <button 
            className="btn-close" 
            onClick={toggleModal}
            aria-label="Cerrar modal"
            title="Cerrar (Escape)"
            disabled={isLoading}
          >
            ✖
          </button>
        </div>

        <div className="modal-body text-center">
          {isLoading ? (
            <div className="loading-state">
              <div className="spinner" aria-hidden="true"></div>
              <p className="mt-3" aria-live="polite">
                {loadingText}
              </p>
            </div>
          ) : (
            <>
              <div className="spinner" aria-hidden="true"></div>
              <p 
                id="modal-description" 
                className="mt-3"
              >
                {message}
              </p>
            </>
          )}

          {error && (
            <div 
              className="error-message mt-3" 
              role="alert"
              aria-live="assertive"
            >
              <p className="text-danger">
                ⚠️ {error}
              </p>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <a
            href={whatsappUrl}
            className={`btn btn-success ${isLoading ? 'btn-loading' : ''}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={handleWhatsAppClick}
            aria-describedby="whatsapp-description"
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <span className="btn-spinner" aria-hidden="true"></span>
                {loadingText}
              </>
            ) : (
              buttonText
            )}
          </a>
          <div 
            id="whatsapp-description" 
            className="sr-only"
          >
            Se abrirá WhatsApp en una nueva ventana
          </div>
        </div>
      </div>
    </div>
  );
}

// Definición de PropTypes para validación
Modal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  toggleModal: PropTypes.func.isRequired,
  title: PropTypes.string,
  message: PropTypes.string,
  whatsappUrl: PropTypes.string,
  buttonText: PropTypes.string,
  onError: PropTypes.func,
  loadingText: PropTypes.string,
};

// Valores por defecto
Modal.defaultProps = {
  title: "Conectando...",
  message: "Nos pondremos en contacto a través de WhatsApp si le da click al botón de ir a WhatsApp.",
  whatsappUrl: "https://api.whatsapp.com/send/?phone=51995092832&text=Me+gustar%C3%ADa+mayor+informaci%C3%B3n+sobre+la+terapia+de+conducta&type=phone_number&app_absent=0",
  buttonText: "Ir a WhatsApp",
  onError: null,
  loadingText: "Cargando...",
};

export default Modal;