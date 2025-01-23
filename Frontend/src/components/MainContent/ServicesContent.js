import React, { useEffect, useState } from "react";
import $ from "jquery";
import 'owl.carousel';
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";

const ServicesContent = (toggleModal) => {
    const [selectedTerapia, setSelectedTerapia] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
   
    const terapiasInfo = {
        lectoEscritura: {
            title: "LECTO-ESCRITURA",
            image: "https://th.bing.com/th/id/OIG4.Lx0DI4cJvITiZ.MhyBou?pid=ImgGn",
            description: "En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños, utilizando métodos innovadores y personalizados.",
        },
        conductal: {
            title: "CONDUCTAL",
            image: "https://th.bing.com/th/id/OIG1.3rx.KXoMCiGOUzV9cq5W?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad, impulsividad, ansiedad y depresión. Nuestro enfoque ayuda a mejorar la calidad de vida, comenzando con la modificación de conductas, clave para el bienestar y desarrollo personal de niños, adolescentes y adultos.",
        },
        lenguaje: {
            title: "DE LENGUAJE",
            image: "https://th.bing.com/th/id/OIG2.QuFUsnwlkYLs3vu.qUB6?pid=ImgGn",
            description: "Enfocada en mejorar las habilidades comunicativas, esta terapia ayuda a niños con dificultades de habla y lenguaje.",
        },
        // Agrega más terapias aquí
        ocupacional: {
            title: "OCUPACIONAL",
            image: "https://th.bing.com/th/id/OIG3.FUFQGAdUlCUv63tDareQ?pid=ImgGn",
            description: "Enfocada en la ocupación u.u.",
        },

        aprendizaje: {
            title: "DE APRENDIZAJE",
            image: "https://th.bing.com/th/id/OIG1._conMoxJM08J1VjdUtoQ?pid=ImgGn",
            description: "Enfocada en el aprendizaje u.u.",
        },
        autismo: {
            title: "AUTISMO",
            image: "https://th.bing.com/th/id/OIG1.ZSdwi6SX6wb4VkHBu2B0?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Trastorno del Espectro Autista (TEA). Utilizamos técnicas propias para ayudar a mejorar la comunicación, la interacción social y la adaptación al entorno. Reconocemos que el autismo se manifiesta de diversas maneras, por lo que adaptamos nuestras terapias para potenciar las habilidades de cada paciente, favoreciendo su desarrollo en áreas como la memoria, el arte o la tecnología.",
        },
        down: {
            title: "SÍNDROME DE DOWN",
            image: "https://th.bing.com/th/id/OIG3.kjBcmrNg0BHo1aWQbqJQ?pid=ImgGn",
            description: "Enfocada en el Síndrome de down u.u.",
        },
        intelectual: {
            title: "DISCAPACIDAD INTELECTUAL",
            image: "https://th.bing.com/th/id/OIG2.ylBCpQ.AGKZwEqyKqXQQ?pid=ImgGn",
            description: "Enfocada en la discapacidad intelectual u.u.",
        },
    };

    const openModal = (terapiaId) => {
        setSelectedTerapia(terapiasInfo[terapiaId]);
        setIsModalOpen(true);
    };

    const closeModal = () => {
        setIsModalOpen(false);
    };

    const scrollToSection = () => {
        const section = document.getElementById("terapias");
        if (section) {
            section.scrollIntoView({ behavior: "smooth" });
        }
    };

    useEffect(() => {
        if ($(".testimonial-carousel").length) {
            $(".testimonial-carousel").owlCarousel({
                items: 1,
                loop: true,
                autoplay: true,
                autoplayTimeout: 3000,
                smartSpeed: 1000,
            });
        }
    }, []);

  return (
    <>
        <div class="container-fluid page-header" style={{marginBottom: "90px"}}>
        <div class="container">
            <div class="d-flex flex-column justify-content-center" style={{minHeight: "300px"}}>
                <h3 class="display-4 text-white text-uppercase">Servicios</h3>
                <div class="d-inline-flex text-white">
                    <p class="m-0 text-uppercase"><a class="text-white" href="">Inicio</a></p>
                    <i class="fa fa-angle-double-right pt-1 px-3"></i>
                    <p class="m-0 text-uppercase">servicios</p>
                </div>
            </div>
        </div>
    </div>
    </>
  );
};

export default ServicesContent;
