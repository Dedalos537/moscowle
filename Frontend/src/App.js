import React, { useState } from "react";
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
    <><div className="App">
      <Navbar handleNavigation={handleNavigation} activeContent={activeContent} />

      <div className={`transition-content ${activeContent === "home" ? "show" : ""}`}>
        {activeContent === "home" && <MainContent handleNavigation={handleNavigation}/>}
      </div>

      <div className={`transition-content ${activeContent === "about" ? "show" : ""}`}>
        {activeContent === "about" && <AboutContent />}
      </div>

      <div className={`transition-content ${activeContent === "services" ? "show" : ""}`}>
        {activeContent === "services" && <ServicesContent />}
      </div>

      <div className={`transition-content ${activeContent === "contact" ? "show" : ""}`}>
        {activeContent === "contact" && <ContactContent />}
      </div>
      <div className={`transition-content ${activeContent === "login" ? "show" : ""}`}/>
      {activeContent === "login" && <Login handleNavigation={handleNavigation}/>}</div>
      <Footer handleNavigation={handleNavigation} activeContent={activeContent} />
      <Modal  handleNavigation={handleNavigation} activeContent={activeContent} isOpen={isModalOpen} toggleModal={toggleModal} />
    </>
  );
}

export default App;