import React from "react";

const AboutContent = () => {
  return (
    <div>
      {/* Encabezado */}
      <div className="container-fluid page-header mb-5">
        <div className="container">
          <div className="d-flex flex-column justify-content-center" style={{ minHeight: "300px" }}>
            <h3 className="display-4 text-white text-uppercase">Acerca</h3>
            <div className="d-inline-flex text-white">
              <p className="m-0 text-uppercase">
                <a className="text-white" href="/">Inicio</a>
              </p>
              <i className="fa fa-angle-double-right pt-1 px-3"></i>
              <p className="m-0 text-uppercase">Acerca</p>
            </div>
          </div>
        </div>
      </div>

      {/* Misión y Visión */}
      <div className="container mb-5">
        <div className="row g-4">
          {/* Misión */}
          <div className="col-md-6">
            <div className="bg-light p-4 rounded shadow h-100 text-center">
              <i className="fa fa-bullseye fa-2x text-primary mb-3"></i>
              <h4 className="text-uppercase">Misión</h4>
              <p className="mt-3">
                Brindar una educación integral, inclusiva y de calidad a personas con habilidades diferentes, 
                potenciando sus capacidades individuales mediante métodos pedagógicos innovadores y personalizados. 
                Fomentamos el desarrollo emocional, social y cognitivo de nuestros estudiantes en un entorno de respeto, 
                empatía y equidad, trabajando de la mano con las familias y la comunidad para promover una sociedad más justa e inclusiva.
              </p>
            </div>
          </div>

          {/* Visión */}
          <div className="col-md-6">
            <div className="bg-light p-4 rounded shadow h-100 text-center">
              <i className="fa fa-eye fa-2x text-success mb-3"></i>
              <h4 className="text-uppercase">Visión</h4>
              <p className="mt-3">
                Ser reconocidos como un centro educativo líder en la atención y formación de personas con habilidades diferentes, 
                destacando por la implementación de metodologías de enseñanza innovadoras y por nuestro compromiso con la inclusión social. 
                Aspiramos a transformar la percepción de la sociedad, eliminando prejuicios y construyendo un futuro donde la diversidad 
                de capacidades sea valorada y respetada.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Mapa */}
      <div className="container mb-5">
        <div className="bg-light p-3 rounded shadow">
          <h4 className="text-uppercase text-center mb-3">
            <i className="fa fa-map-marker-alt text-success me-2"></i>  Ubicación
          </h4>
          <div className="embed-responsive embed-responsive-16by9">
            <iframe
              className="embed-responsive-item w-100"
              height="450"
              src="https://www.google.com/maps/embed?pb=!1m14!1m8!1m3!1d248.34166205759357!2d-80.64536749386156!3d-5.1890914665209!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x904a1a8fdc7e630b%3A0xfb595f6d8eb99d97!2sCentro%20de%20Terapias%20Juan%20Pablo%20II!5e0!3m2!1sfr!2spe!4v1736303806967!5m2!1sfr!2spe"
              style={{ border: "0" }}
              allowFullScreen=""
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              title="Ubicación del Centro de Terapias Juan Pablo II"
            ></iframe>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutContent;


