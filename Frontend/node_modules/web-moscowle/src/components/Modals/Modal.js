import React, { useState, useEffect } from "react";

import "./Modal.css";


function Modal({ isOpen, toggleModal }) {

  useEffect(() => {

    // Bloquea el deslizamiento de la página cuando el modal está abierto

    if (isOpen) {

      document.body.style.overflow = "hidden"; // Bloquea el scroll

    } else {

      document.body.style.overflow = ""; // Restablece el scroll cuando el modal se cierra

    }


    // Limpieza en el efecto para restaurar el scroll cuando el modal se cierre

    return () => {

      document.body.style.overflow = ""; // Asegúrate de restaurar el scroll

    };

  }, [isOpen]);


  const handleClickOutside = (e) => {

    // Cierra el modal cuando se hace clic fuera de la caja modal

    if (e.target.classList.contains("modal-container")) {

      toggleModal();

    }

  };


  return (

    <div

      className={`modal-container ${isOpen ? "show" : ""}`}

      onClick={handleClickOutside} // Detectar clic fuera del modal

    >

      <div className="modal-content" onClick={(e) => e.stopPropagation()}>

        <div className="modal-header">

          <h5 className="modal-title">Conectando...</h5>

          <button className="btn-close" onClick={toggleModal}>

            ✖

          </button>

        </div>

        <div className="modal-body text-center">

          <div className="spinner"></div>

          <p className="mt-3">

            Nos pondremos en contacto a través de WhatsApp si le da click al

            botón de ir a WhatsApp.

          </p>

        </div>

        <div className="modal-footer">

          <a

            href="https://api.whatsapp.com/send/?phone=51995092832&text=Me+gustar%C3%ADa+mayor+informaci%C3%B3n+sobre+la+terapia+de+conducta&type=phone_number&app_absent=0"

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

}
export default Modal;
