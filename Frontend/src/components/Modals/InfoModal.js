import React, { useState, useEffect } from 'react';
import './Modal.css'; // Asegúrate de importar tu archivo CSS

const InfoModal = ({ isOpen, onRequestClose, selectedTerapia }) => {
    const [imageLoaded, setImageLoaded] = useState(true);
    const [imageVisible, setImageVisible] = useState(false); // Estado para controlar la visibilidad de la imagen

    useEffect(() => {
        // Bloquea el deslizamiento de la página cuando el modal está abierto
        if (isOpen) {
            document.body.style.overflow = 'hidden'; // Bloquea el scroll
            setImageVisible(true); // Muestra la imagen al abrir el modal
            setImageLoaded(true); // Restablece el estado de carga de la imagen
        } else {
            document.body.style.overflow = ''; // Restablece el scroll cuando el modal se cierra
        }

        // Limpieza en el efecto para restaurar el scroll cuando el modal se cierre
        return () => {
            document.body.style.overflow = ''; // Asegúrate de restaurar el scroll
        };
    }, [isOpen]);

    const handleClickOutside = (e) => {
        // Verifica si el clic es fuera del contenido del modal
        if (e.target.classList.contains('modal-container')) {
            onRequestClose();
        }
    };

    const handleImageLoad = () => {
        setImageLoaded(true);
    };

    const handleImageError = () => {
        setImageVisible(false); // Oculta la imagen si hay un error al cargar
    };

    if (!selectedTerapia) return null; // Asegúrate de que haya una terapia seleccionada

    return (
        <div
            className={`modal-container ${isOpen ? 'show' : ''}`}
            onClick={handleClickOutside} // Detectar clic fuera del modal
        >
            <div
                className={`modal-content ${isOpen ? 'fade-in' : 'fade-out'}`}
                onClick={(e) => e.stopPropagation()} // Previene el cierre al hacer clic dentro del modal
                style={{ width: '600px', height: '400px', display: 'flex', flexDirection: 'column' }} // Tamaño fijo del modal
            >

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '20px' }}>
                    <h2 style={{ color: '#4CAF50', margin: 0 }}>{selectedTerapia.title}</h2>
                    <button className="btn btn-close" onClick={onRequestClose} style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
                        <i className="fa fa-times fa-lg text-primary"></i> {/* Icono de cerrar */}
                    </button>
                </div>


                <div style={{ display: 'flex', flex: 1 }}>
                    {imageVisible && (
                        <div style={{ flex: 1 }}>
                            <img
                                src={selectedTerapia.image}
                                alt={selectedTerapia.title}
                                style={{
                                    width: '100%',
                                    height: '100%', // Ocupa todo el alto
                                    objectFit: 'cover', // Mantiene la proporción de la imagen
                                    borderRadius: '10px',
                                    opacity: imageLoaded ? 1 : 0,
                                    transition: 'opacity 0.5s ease-in-out'
                                }}
                                onLoad={handleImageLoad} // Set image loaded to true when the image is loaded
                                onError={handleImageError} // Handle image load error
                            />
                        </div>
                    )}
                    <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
                        <p style={{ maxHeight: '170px', overflowY: 'auto' }}>{selectedTerapia.description}</p>
                    </div>
                </div>
                <div style={{ padding: '20px', textAlign: 'center' }}>
                    <a
                        href="https://api.whatsapp.com/send/?phone=51995092832&type=phone_number&app_absent=0"
                        className="btn btn-success"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Ir a WhatsApp
                    </a>
                </div>
            </div>
        </div>
    );
};

export default InfoModal;