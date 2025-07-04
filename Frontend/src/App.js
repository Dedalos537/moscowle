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
import AdminDashboard from "./components/Admin/Dashboard";

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

  // Definir rutas donde mostrar Navbar y Footer
  const showNavAndFooter = ["/", "/about", "/services", "/contact"];
  const currentPath = window.location.pathname;

  return (
    <Router>
      <div className="App">
        {showNavAndFooter.includes(currentPath) && (
          <Navbar handleNavigation={handleNavigation} activeContent={activeContent} />
        )}
        <Routes>
          <Route path="/" element={<MainContent handleNavigation={handleNavigation} />} />
          <Route path="/about" element={<AboutContent />} />
          <Route path="/services" element={<ServicesContent />} />
          <Route path="/contact" element={<ContactContent />} />
          <Route path="/login" element={<Login handleNavigation={handleNavigation} />} />
          <Route path="/dashboard" element={<AdminDashboard />} />
          <Route path="/cursos" element={
            <Suspense fallback={<div>Cargando...</div>}>
              <CoursesComponent />
            </Suspense>
          } />
        </Routes>
        {showNavAndFooter.includes(currentPath) && (
          <Footer handleNavigation={handleNavigation} activeContent={activeContent} />
        )}
        <Modal handleNavigation={handleNavigation} activeContent={activeContent} isOpen={isModalOpen} toggleModal={toggleModal} />
      </div>
    </Router>
  );
}

export default App;