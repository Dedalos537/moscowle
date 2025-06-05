import React, { useState } from "react";

const Footer = ({handleNavigation}) => {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [showPrivacidad, setShowPrivacidad] = useState(false);
  const [showTerminos, setShowTerminos] = useState(false);

  const services = [
    { label: "Terapias", target: "services" },
    { label: "Terapias Integrales", target: "services" },
    { label: "Apoyo Virtual", target: "services" },
    { label: "Material Concreto", target: "services" },
  ];


  const handleInputChange = (e) => setEmail(e.target.value);

  const sendEmail = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch("http://localhost:5000/send-email", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ userEmail: email }),
      });

      const data = await response.json();
      if (response.ok) {
        setMessage("¡Correo enviado con éxito! Pronto nos comunicaremos contigo.");
        setEmail("");
      } else {
        setMessage(data.message || "Hubo un error al enviar el correo.");
      }
    } catch (error) {
      console.error("Error al enviar el correo:", error);
      setMessage("Hubo un error al enviar el correo. Inténtalo más tarde.");
    }
  };

  return (
    <>
      {/* Modal Privacidad */}
      {showPrivacidad && (
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content bg-dark text-white p-4">
              <h5>Política de Privacidad</h5>
              <p>Esta es la información relacionada con nuestra política de privacidad...</p>
              <button className="btn btn-light mt-3" onClick={() => setShowPrivacidad(false)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}

      {/* Modal Términos */}
      {showTerminos && (
        <div className="modal fade show d-block" tabIndex="-1">
          <div className="modal-dialog modal-dialog-centered">
            <div className="modal-content bg-dark text-white p-4">
              <h5>Términos y Condiciones</h5>
              <p>Estos son los términos y condiciones de uso del sitio...</p>
              <button className="btn btn-light mt-3" onClick={() => setShowTerminos(false)}>Cerrar</button>
            </div>
          </div>
        </div>
      )}

      {/* Footer Principal */}
      <div className="container-fluid bg-dark text-white py-5 px-sm-3 px-lg-5" style={{ marginTop: "90px" }}>
        <div className="row pt-5">
          <div className="col-lg-7 col-md-12">
            <div className="row">
              <div className="col-md-6 mb-5">
                <h5 className="text-primary text-uppercase mb-4" style={{ letterSpacing: "5px" }}>Contáctanos</h5>
                <p><i className="fa fa-envelope mr-2"></i>informes@centrojuanpabloii.com</p>
                <div className="d-flex mt-4">
                  <a className="btn btn-outline-light btn-square mr-2" href="#"><i className="fab fa-twitter"></i></a>
                  <a className="btn btn-outline-light btn-square mr-2" href="#"><i className="fab fa-facebook-f"></i></a>
                  <a className="btn btn-outline-light btn-square" href="#"><i className="fab fa-instagram"></i></a>
                </div>
              </div>
              <div className="col-md-6 mb-5">
                <h5 className="text-primary text-uppercase mb-4" style={{ letterSpacing: "5px" }}>Nuestros Servicios</h5>
                <div className="d-flex flex-column">
                  {services.map((service, index) => (
                    <a
                      key={index}
                      className="text-white mb-2"
                      href="#!"
                      onClick={() => handleNavigation("services")}
                    >
                      <i className="fa fa-angle-right mr-2"></i>{service.label}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="col-lg-5 col-md-12 mb-5">
            <h5 className="text-primary text-uppercase mb-4" style={{ letterSpacing: "5px" }}>Cartas</h5>
            <p>Nos puede contactar directamente enviando su correo electrónico mediante este apartado.</p>
            <form onSubmit={sendEmail}>
              <div className="input-group">
                <input
                  type="email"
                  className="form-control border-light"
                  style={{ padding: "30px" }}
                  placeholder="Su dirección de Correo Electrónico"
                  value={email}
                  onChange={handleInputChange}
                  required
                />
                <div className="input-group-append">
                  <button type="submit" className="btn btn-primary px-4">Enviar</button>
                </div>
              </div>
              {message && <p style={{ marginTop: "20px" }}>{message}</p>}
            </form>
          </div>
        </div>
      </div>

      {/* Footer Inferior */}
      <div className="container-fluid bg-dark text-white border-top py-4 px-sm-3 px-md-5">
        <div className="row">
          <div className="col-lg-6 text-center text-md-left mb-3 mb-md-0">
            <p className="m-0 text-white">&copy; <a className="text-primary" href="#">Centro JuanPabloII</a>. Todos los Derechos Reservados.</p>
          </div>
          <div className="col-lg-6 text-center text-md-right">
            <ul className="nav d-inline-flex">
              <li className="nav-item">
                <a className="nav-link text-white py-0" href="#!" onClick={() => setShowPrivacidad(true)}>Privacidad</a>
              </li>
              <li className="nav-item">
                <a className="nav-link text-white py-0" href="#!" onClick={() => setShowTerminos(true)}>Términos</a>
              </li>
              <li className="nav-item">
                <a className="nav-link text-white py-0" href="#!" onClick={() => handleNavigation("contact")}>Ayuda</a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </>
  );
};

export default Footer;






