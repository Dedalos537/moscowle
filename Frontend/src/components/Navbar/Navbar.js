import React, { useState } from "react";

const Navbar = ({ handleNavigation, activeContent }) => {
  const [isMobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleMenuToggle = () => {
    setMobileMenuOpen(!isMobileMenuOpen);
  };

  const handleLinkClick = (content) => {
    handleNavigation(content);
    setMobileMenuOpen(false); // Cierra el menú al cambiar de pestaña
  };

  // Nueva función para manejar navegación a secciones específicas
  const handleSectionNavigation = (sectionId) => {
    // Primero navegar a la página de servicios
    handleNavigation("services");
    
    // Esperar un poco para que se renderice la página y luego hacer scroll
    setTimeout(() => {
      const section = document.getElementById(sectionId);
      if (section) {
        section.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
    
    setMobileMenuOpen(false);
  };

  return (
    <>
      <div className="container-fluid d-none d-lg-block">
        <div className="row align-items-center py-4 px-xl-5">
          <div className="col-lg-3">
            <a href="" className="text-decoration-none">
              <h1 className="m-0">
                <span className="text-primary">CENTRO DE TERAPIAS</span> JUAN
                PABLO II
              </h1>
            </a>
          </div>
          <div className="col-lg-7 text-right">
            <div className="d-inline-flex align-items-center">
              <i className="fa fa-2x fa-envelope text-primary mr-3"></i>
              <div className="text-left">
                <h3 className="font-weight-semi-bold mb-1">Escríbenos</h3>
                <h6>informes@centrojuanpabloii.com</h6>
              </div>
            </div>
          </div>
          <div className="col-lg-2 text-right">
            <button
              className="btn btn-primary px-4 py-2 font-weight-bold"
              onClick={() => handleNavigation("login")}
            >
              <i className="fa fa-user mr-2"></i>Ingresar
            </button>
          </div>
        </div>

        <div className="container-fluid">
          <div className="row border-top px-xl-5">
            <div className="col-lg-3 d-none d-lg-block">
              <a
                className="d-flex align-items-center justify-content-between bg-secondary w-100 text-decoration-none"
                data-toggle="collapse"
                href="#navbar-vertical"
                style={{ height: "67px", padding: "0 30px" }}
              >
                <h5 className="text-primary m-0">
                  <i className="fa fa-book-open mr-2"></i>Servicios
                </h5>
                <i className="fa fa-angle-down text-primary"></i>
              </a>
              <nav
                className="collapse position-absolute navbar navbar-vertical navbar-light align-items-start p-0 border border-top-0 border-bottom-0 bg-light"
                id="navbar-vertical"
                style={{ width: "calc(100% - 30px)", zIndex: "9" }}
              >
                <div className="navbar-nav w-100">
                  <div className="nav-item dropdown">
                    <a href="#!" className="nav-link" data-toggle="dropdown">
                      Terapias{" "}
                      <i className="fa fa-angle-down float-right mt-1"></i>
                    </a>
                    <div className="dropdown-menu position-absolute bg-secondary border-0 rounded-0 w-100 m-0">
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("Terapias")}>
                        LECTO-ESCRITURA
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("Terapias")}>
                        CONDUCTUAL
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("Terapias")}>
                        DE LENGUAJE
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("Terapias")}>
                        DE APRENDIZAJE
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("Terapias")}>
                        OCUPACIONAL
                      </a>
                    </div>
                  </div>
                  <div className="nav-item dropdown">
                    <a href="#!" className="nav-link" data-toggle="dropdown">
                      Terapias Integrales{" "}
                      <i className="fa fa-angle-down float-right mt-1"></i>
                    </a>
                    <div className="dropdown-menu position-absolute bg-secondary border-0 rounded-0 w-100 m-0">
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                        AUTISMO (TEA)
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                        TDA
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                        TDAH
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                        SÍNDROME DE DOWN
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                        DISCAPACIDAD INTELECTUAL
                      </a>
                    </div>
                  </div>
                  <div className="nav-item dropdown">
                    <a href="#!" className="nav-link" data-toggle="dropdown">
                      Apoyo Virtual{" "}
                      <i className="fa fa-angle-down float-right mt-1"></i>
                    </a>
                    <div className="dropdown-menu position-absolute bg-secondary border-0 rounded-0 w-100 m-0">
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                        COMUNICACIÓN ORAL
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                        LECTO-ESCRITURA
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                        MATEMÁTICAS
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                        DESARROLLO COGNITIVO
                      </a>
                    </div>
                  </div>
                  <div className="nav-item dropdown">
                    <a href="#!" className="nav-link" data-toggle="dropdown">
                      Material Concreto
                      <i className="fa fa-angle-down float-right mt-1"></i>
                    </a>
                    <div className="dropdown-menu position-absolute bg-secondary border-0 rounded-0 w-100 m-0">
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("MaterialConcreto")}>
                        COMUNICACIÓN ORAL
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("MaterialConcreto")}>
                        LECTO-ESCRITURA
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("MaterialConcreto")}>
                        MATEMÁTICAS
                      </a>
                      <a href="#!" className="dropdown-item" onClick={() => handleSectionNavigation("MaterialConcreto")}>
                        DESARROLLO COGNITIVO
                      </a>
                    </div>
                  </div>
                </div>
              </nav>
            </div>
            <div className="col-lg-9">
              <nav className="navbar navbar-expand-lg bg-light navbar-light py-3 py-lg-0 px-0">
                <a href="#!" className="text-decoration-none d-block d-lg-none">
                  <h1 className="m-0">
                    <span className="text-primary">CENTRO</span> JUAN PABLO II
                  </h1>
                </a>
                <button
                  type="button"
                  className="navbar-toggler"
                  data-toggle="collapse"
                  data-target="#navbarCollapse"
                >
                  <span className="navbar-toggler-icon"></span>
                </button>
                <div
                  className="collapse navbar-collapse justify-content-between"
                  id="navbarCollapse"
                >
                  <div className="navbar-nav py-0">
                    <a
                      href="#!"
                      className={`nav-item nav-link ${
                        activeContent === "home" ? "active" : ""
                      }`}
                      onClick={() => handleNavigation("home")}
                    >
                      Inicio
                    </a>
                    <a
                      href="#!"
                      className={`nav-item nav-link ${
                        activeContent === "about" ? "active" : ""
                      }`}
                      onClick={() => handleNavigation("about")}
                    >
                      Acerca
                    </a>
                    <a
                      href="#!"
                      className={`nav-item nav-link ${
                        activeContent === "services" ? "active" : ""
                      }`}
                      onClick={() => handleNavigation("services")}
                    >
                      Servicios
                    </a>
                    <a
                      href="#!"
                      className={`nav-item nav-link ${
                        activeContent === "contact" ? "active" : ""
                      }`}
                      onClick={() => handleNavigation("contact")}
                    >
                      Contáctanos
                    </a>
                  </div>
                </div>
              </nav>
            </div>
          </div>
        </div>
      </div>
      <div className="d-lg-none pb-2">
        <div className="row align-items-center py-4 px-xl-5">
          <div className="col-12 text-center">
            <h1 className="m-0">
              <span className="text-primary">CENTRO DE TERAPIAS</span> JUAN
              PABLO II
            </h1>

            <div className="mt-4">
              <div className="d-inline-flex align-items-center mt-2">
                <i className="fa fa-envelope text-primary mr-2 fa-lg"></i>

                <div className="text-left">
                  <h6 className="m-0">informes@centrojuanpabloii.com</h6>
                </div>
              </div>
              <div className="mt-3">
                <button
                  className="btn btn-primary px-4 py-2"
                  onClick={() => handleLinkClick("login")}
                >
                  <i className="fa fa-user mr-2"></i>Ingresar
                </button>
              </div>
            </div>
          </div>
        </div>

        <button
          className="navbar-toggler"
          type="button"
          onClick={handleMenuToggle}
        >
          <i className="fa fa-bars fa-lg text-primary"></i>{" "}
          {/* Icono de hamburguesa */}
        </button>

        <div
          className={`collapse ${isMobileMenuOpen ? "show" : ""}`}
          id="mobileNavbar"
        >
          <div className="bg-light p-3">
            <a
              href="#!"
              className="nav-link"
              onClick={() => handleLinkClick("home")}
            >
              Inicio
            </a>

            <a
              href="#!"
              className="nav-link"
              onClick={() => handleLinkClick("about")}
            >
              Acerca
            </a>

            <a
              href="#!"
              className="nav-link"
              onClick={() => handleLinkClick("services")}
            >
              Servicios
            </a>

            {/* Menú móvil expandido para servicios */}
            <div className="ml-3">
              <div className="nav-link font-weight-bold text-primary" style={{fontSize: '0.9rem'}}>
                Terapias Especializadas
              </div>
              <div className="ml-2">
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("Terapias")}>
                  Lecto-escritura
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("Terapias")}>
                  Conductual
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("Terapias")}>
                  De Lenguaje
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("Terapias")}>
                  De Aprendizaje
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("Terapias")}>
                  Ocupacional
                </a>
              </div>
              
              <div className="nav-link font-weight-bold text-success" style={{fontSize: '0.9rem'}}>
                Terapias Integrales
              </div>
              <div className="ml-2">
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                  Autismo (TEA)
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                  TDA
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                  TDAH
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                  Síndrome de Down
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("TerapiasIntegrales")}>
                  Discapacidad Intelectual
                </a>
              </div>
              
              <div className="nav-link font-weight-bold text-info" style={{fontSize: '0.9rem'}}>
                Apoyo Virtual
              </div>
              <div className="ml-2">
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                  Comunicación Oral
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                  Lecto-escritura
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                  Matemáticas
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("ApoyoVirtual")}>
                  Desarrollo Cognitivo
                </a>
              </div>
              
              <div className="nav-link font-weight-bold text-warning" style={{fontSize: '0.9rem'}}>
                Material Concreto
              </div>
              <div className="ml-2">
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("MaterialConcreto")}>
                  Comunicación Oral
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("MaterialConcreto")}>
                  Lecto-escritura
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("MaterialConcreto")}>
                  Matemáticas
                </a>
                <a href="#!" className="nav-link text-muted" style={{fontSize: '0.85rem'}} onClick={() => handleSectionNavigation("MaterialConcreto")}>
                  Desarrollo Cognitivo
                </a>
              </div>
            </div>

            <a
              href="#!"
              className="nav-link"
              onClick={() => handleLinkClick("contact")}
            >
              Contáctanos
            </a>

            <div className="border-top pt-3 mt-2">
              <button
                className="btn btn-primary btn-block"
                onClick={() => handleLinkClick("login")}
              >
                <i className="fa fa-user mr-2"></i>Ingresar
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default Navbar;