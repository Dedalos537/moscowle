import React, { useState } from "react";
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

import AdminLayout from "./pages/admin/AdminLayout";
import Contactos from "./pages/admin/Contactos";
import Usuarios from "./pages/admin/Usuarios";
import Perfil from "./pages/admin/Perfil";


import "./App.css";
import "owl.carousel/dist/assets/owl.carousel.min.css";
import "owl.carousel/dist/assets/owl.theme.default.min.css";
import "owl.carousel/dist/owl.carousel.min.js";

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
            <div className="App">
              <Navbar handleNavigation={handleNavigation} activeContent={activeContent} />

              {activeContent === "home" && <MainContent />}
              {activeContent === "about" && <AboutContent />}
              {activeContent === "services" && <ServicesContent />}
              {activeContent === "contact" && <ContactContent />}

              <Footer handleNavigation={handleNavigation} activeContent={activeContent} />
              <Modal isOpen={isModalOpen} toggleModal={toggleModal} />
            </div>
          }
        />

        {/* Rutas del panel de administración */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route path="contactos" element={<Contactos />} />
          <Route path="usuarios" element={<Usuarios />} />
          <Route path="perfil" element={<Perfil />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
