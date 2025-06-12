// App.js - Enfoque alternativo con lazy loading
import React, { useState, Suspense } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route
} from "react-router-dom";
import Navbar from "./components/Navbar/Navbar";
import Footer from "./components/Footer/Footer";
import MainContent from "./components/MainContent/MainContent";
import AboutContent from "./components/MainContent/AboutContent"; 
import ServicesContent from "./components/MainContent/ServicesContent"; 
import ContactContent from "./components/MainContent/ContactContent"; 
import Modal from "./components/Modals/Modal";
import Login from "./components/Auth/Login";
import "./App.css";
import "owl.carousel/dist/assets/owl.carousel.min.css";
import "owl.carousel/dist/assets/owl.theme.default.min.css";
import "owl.carousel/dist/owl.carousel.min.js";

// Carga lazy del componente LMS para evitar que su CSS se cargue hasta que sea necesario
const CoursesComponent = React.lazy(() => import("./components/Lms/Principal"));

function App() {
  const [isModalOpen, setModalOpen] = useState(false);
  const [activeContent, setActiveContent] = useState("home");

  const toggleModal = () => {
    setModalOpen(!isModalOpen);
  };

  const handleNavigation = (content) => {
    setActiveContent(content);
  };

  return (
    <Router>
      <Routes>
        {/* Rutas principales del sitio web */}
        <Route
          path="/"
          element={
            <div className="App" data-theme="main-site">
              <Navbar handleNavigation={handleNavigation} activeContent={activeContent} />

              {activeContent === "home" && <MainContent />}
              {activeContent === "about" && <AboutContent />}
              {activeContent === "services" && <ServicesContent />}
              {activeContent === "contact" && <ContactContent />}
              {activeContent === "login" && <Login handleNavigation={handleNavigation}/>}

              <Footer handleNavigation={handleNavigation} activeContent={activeContent} />
              <Modal isOpen={isModalOpen} toggleModal={toggleModal} />
            </div>
          }
        />

        {/* Rutas del panel de administración con carga lazy */}
        <Route 
          path="/lms/*" 
          element={
            <div className="lms-root" data-theme="lms">
              <Suspense fallback={
                <div className="lms-loading">
                  <div className="loading-spinner">Cargando LMS...</div>
                </div>
              }>
                <CoursesComponent />
              </Suspense>
            </div>
          } 
        />
      </Routes>
    </Router>
  );
}

export default App;