import React, { useEffect, useState } from "react";
import $ from "jquery";
import 'owl.carousel';
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";
import InfoModal from '../Modals/InfoModal';
const ServicesContent = () => {
    const [selectedTerapia, setSelectedTerapia] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
   
    const terapiasInfo = {
        lectoEscritura: {
            title: "LECTO-ESCRITURA",
            image: "https://th.bing.com/th/id/OIG4.Lx0DI4cJvITiZ.MhyBou?pid=ImgGn",
            description: "En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños, utilizando métodos innovadores y personalizados que nos permiten alcanzar grandes logros.",
            category: "Terapias"
        },
        conductual: {
            title: "CONDUCTUAL",
            image: "https://th.bing.com/th/id/OIG1.3rx.KXoMCiGOUzV9cq5W?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad, impulsividad, ansiedad y depresión. Nuestro enfoque ayuda a mejorar la calidad de vida, comenzando con la modificación de conductas, clave para el bienestar y desarrollo personal de niños, adolescentes y adultos.",
            category: "Terapias"
        },
        lenguaje: {
            title: "DE LENGUAJE",
            image: "https://th.bing.com/th/id/OIG2.QuFUsnwlkYLs3vu.qUB6?pid=ImgGn",
            description: "Es un proceso que se enfoca en ayudar a aquellas personas que enfrentan dificultades para hablar y sus consecuencias como entender, leer o escribir. A través de técnicas personalizadas, el Centro de Terapias Juan Pablo II soluciona problemas como la articulación incorrecta, el retraso en el desarrollo del habla, y dificultades en la comprensión y producción del lenguaje. El objetivo es facilitar una comunicación efectiva, que permita a cada persona desarrollarse plenamente en su entorno.",
            category: "Terapias"
        },
        aprendizaje: {
            title: "DE APRENDIZAJE",
            image: "https://th.bing.com/th/id/OIG1._conMoxJM08J1VjdUtoQ?pid=ImgGn",
            description: "Terapia especializada en superar dificultades de aprendizaje, utilizando técnicas personalizadas para mejorar el rendimiento académico y las habilidades cognitivas de cada paciente.",
            category: "Terapias"
        },
        ocupacional: {
            title: "OCUPACIONAL",
            image: "https://th.bing.com/th/id/OIG3.FUFQGAdUlCUv63tDareQ?pid=ImgGn",
            description: "La terapia ocupacional se enfoca en ayudar a las personas a superar dificultades en actividades cotidianas esenciales como la alimentación, la higiene personal, el control de esfínteres, el estudio y la recreación. En el Centro de Terapias Juan Pablo II, ofrecemos intervenciones personalizadas para fomentar la autosuficiencia y mejorar la calidad de vida de cada paciente.",
            category: "Terapias"
        },
        autismo: {
            title: "AUTISMO (TEA)",
            image: "https://th.bing.com/th/id/OIG1.ZSdwi6SX6wb4VkHBu2B0?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Trastorno del Espectro Autista (TEA). Utilizamos técnicas propias para ayudar a mejorar la comunicación, la interacción social y la adaptación al entorno. Reconocemos que el autismo se manifiesta de diversas maneras, por lo que adaptamos nuestras terapias para potenciar las habilidades de cada paciente, favoreciendo su desarrollo en áreas como la memoria, el arte o la tecnología.",
            category: "Terapias Integrales"
        },
        tda: {
            title: "TDA",
            image: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop",
            description: "Tratamiento especializado para el Trastorno por Déficit de Atención, enfocado en mejorar la concentración, organización y habilidades ejecutivas a través de técnicas terapéuticas personalizadas.",
            category: "Terapias Integrales"
        },
        tdah: {
            title: "TDAH",
            image: "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?w=400&h=300&fit=crop",
            description: "Abordaje integral del Trastorno por Déficit de Atención e Hiperactividad, combinando estrategias conductuales y cognitivas para mejorar el autocontrol, la atención y las habilidades sociales.",
            category: "Terapias Integrales"
        },
        down: {
            title: "SÍNDROME DE DOWN",
            image: "https://th.bing.com/th/id/OIG3.kjBcmrNg0BHo1aWQbqJQ?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Síndrome de Down. Utilizamos técnicas propias para mejorar el desarrollo psicomotor, el lenguaje y la autonomía personal. Reconocemos que cada persona presenta fortalezas únicas, por lo que adaptamos nuestras terapias para potenciar sus capacidades individuales, favoreciendo su inclusión social, aprendizaje y desarrollo de habilidades para la vida diaria.",
            category: "Terapias Integrales"
        },
        intelectual: {
            title: "DISCAPACIDAD INTELECTUAL",
            image: "https://th.bing.com/th/id/OIG2.ylBCpQ.AGKZwEqyKqXQQ?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Discapacidad Intelectual. Utilizamos técnicas propias para fortalecer las habilidades cognitivas, la comunicación y la independencia funcional. Reconocemos que cada persona tiene un potencial único, por lo que adaptamos nuestras terapias para desarrollar sus capacidades específicas, favoreciendo su inclusión social, autonomía y el máximo desarrollo de sus competencias personales.",
            category: "Terapias Integrales"
        },
        comunicacionOral: {
            title: "COMUNICACIÓN ORAL",
            image: "https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=400&h=300&fit=crop",
            description: "Apoyo virtual especializado en el desarrollo de habilidades de comunicación oral, utilizando herramientas digitales innovadoras para mejorar la expresión verbal y la comprensión auditiva.",
            category: "Apoyo Virtual"
        },
        lectoEscrituraVirtual: {
            title: "LECTO-ESCRITURA VIRTUAL",
            image: "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=300&fit=crop",
            description: "Programa virtual de apoyo en lectoescritura, diseñado para fortalecer las habilidades de lectura y escritura a través de plataformas digitales interactivas.",
            category: "Apoyo Virtual"
        },
        matematicas: {
            title: "MATEMÁTICAS",
            image: "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400&h=300&fit=crop",
            description: "Apoyo virtual en matemáticas que utiliza metodologías digitales para facilitar el aprendizaje de conceptos numéricos y operaciones matemáticas básicas y avanzadas.",
            category: "Apoyo Virtual"
        },
        desarrolloCognitivo: {
            title: "DESARROLLO COGNITIVO",
            image: "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&h=300&fit=crop",
            description: "Programa virtual enfocado en estimular y desarrollar las funciones cognitivas superiores como memoria, atención, percepción y funciones ejecutivas.",
            category: "Apoyo Virtual"
        }
    };

    const materialConcreto = {
        comunicacionOralMaterial: {
            title: "COMUNICACIÓN ORAL",
            image: "https://images.unsplash.com/photo-1596464716127-f2a82984de30?w=400&h=300&fit=crop",
            description: "Material concreto diseñado para estimular y desarrollar las habilidades de comunicación oral a través de juegos, tarjetas y actividades interactivas.",
            category: "Material Concreto"
        },
        lectoEscrituraMaterial: {
            title: "LECTO-ESCRITURA",
            image: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=300&fit=crop",
            description: "Recursos tangibles y manipulativos para el aprendizaje de la lectura y escritura, incluyendo letras móviles, libros sensoriales y material didáctico especializado.",
            category: "Material Concreto"
        },
        matematicasMaterial: {
            title: "MATEMÁTICAS",
            image: "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=400&h=300&fit=crop",
            description: "Material manipulativo para el aprendizaje de conceptos matemáticos, incluyendo ábacos, bloques lógicos, regletas y otros recursos didácticos concretos.",
            category: "Material Concreto"
        },
        desarrolloCognitivoMaterial: {
            title: "DESARROLLO COGNITIVO",
            image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop",
            description: "Recursos físicos y tangibles diseñados para estimular el desarrollo cognitivo, incluyendo rompecabezas, juegos de memoria y material sensorial especializado.",
            category: "Material Concreto"
        }
    };

    const allServices = { ...terapiasInfo, ...materialConcreto };

    const openModal = (terapiaId) => {
        setSelectedTerapia(allServices[terapiaId]);
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

    const getServicesByCategory = (category) => {
        return Object.entries(allServices).filter(([key, service]) => service.category === category);
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
            {/* Header Section */}
            <div className="container-fluid page-header" style={{
                marginBottom: "90px",
                background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                position: "relative",
                overflow: "hidden"
            }}>
                <div className="position-absolute w-100 h-100" style={{
                    background: "rgba(0,0,0,0.3)",
                    zIndex: 1
                }}></div>
                <div className="container position-relative" style={{zIndex: 2}}>
                    <div className="d-flex flex-column justify-content-center align-items-center text-center" style={{minHeight: "300px"}}>
                        <h1 className="display-3 text-white font-weight-bold mb-3">Nuestros Servicios</h1>
                        <p className="text-white-50 mb-4 lead">Ofrecemos una amplia gama de terapias especializadas para el desarrollo integral</p>
                        <div className="d-inline-flex text-white">
                            <p className="m-0 text-uppercase"><a className="text-white text-decoration-none" href="">Inicio</a></p>
                            <i className="fas fa-angle-double-right pt-1 px-3"></i>
                            <p className="m-0 text-uppercase">Servicios</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Services Content */}
            <div className="container-fluid py-5">
                <div className="container">
                    {/* Terapias Section */}
                    <div className="row mb-5">
                        <div className="col-12">
                            <div className="text-center mb-5">
                                <h2 className="display-4 font-weight-bold text-primary mb-3">Terapias Especializadas</h2>
                                <p className="lead text-muted">Terapias individualizadas para el desarrollo de habilidades específicas</p>
                                <div className="bg-primary mx-auto" style={{width: "80px", height: "4px", borderRadius: "2px"}}></div>
                            </div>
                        </div>
                        {getServicesByCategory("Terapias").map(([key, terapia]) => (
                            <div key={key} className="col-lg-3 col-md-6 mb-4">
                                <div 
                                    className="card h-100 shadow-sm border-0 therapy-card" 
                                    onClick={() => openModal(key)}
                                    style={{
                                        cursor: "pointer",
                                        transition: "all 0.3s ease",
                                        borderRadius: "15px",
                                        overflow: "hidden"
                                    }}
                                >
                                    <div className="position-relative overflow-hidden">
                                        <img 
                                            className="card-img-top" 
                                            src={terapia.image} 
                                            alt={terapia.title}
                                            style={{
                                                height: "200px",
                                                objectFit: "cover",
                                                transition: "transform 0.3s ease"
                                            }}
                                        />
                                        <div className="position-absolute top-0 left-0 w-100 h-100 d-flex align-items-center justify-content-center"
                                             style={{
                                                 background: "rgba(102, 126, 234, 0.8)",
                                                 opacity: 0,
                                                 transition: "opacity 0.3s ease"
                                             }}>
                                            <i className="fas fa-plus-circle text-white" style={{fontSize: "3rem"}}></i>
                                        </div>
                                    </div>
                                    <div className="card-body d-flex flex-column">
                                        <h5 className="card-title font-weight-bold text-primary text-center mb-3">
                                            {terapia.title}
                                        </h5>
                                        <p className="card-text text-muted small flex-grow-1">
                                            {terapia.description.substring(0, 100)}...
                                        </p>
                                        <div className="text-center mt-auto">
                                            <span className="btn btn-outline-primary btn-sm">Ver más detalles</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Terapias Integrales Section */}
                    <div className="row mb-5">
                        <div className="col-12">
                            <div className="text-center mb-5">
                                <h2 className="display-4 font-weight-bold text-success mb-3">Terapias Integrales</h2>
                                <p className="lead text-muted">Programas especializados para condiciones específicas</p>
                                <div className="bg-success mx-auto" style={{width: "80px", height: "4px", borderRadius: "2px"}}></div>
                            </div>
                        </div>
                        {getServicesByCategory("Terapias Integrales").map(([key, terapia]) => (
                            <div key={key} className="col-lg-3 col-md-6 mb-4">
                                <div 
                                    className="card h-100 shadow-sm border-0 therapy-card" 
                                    onClick={() => openModal(key)}
                                    style={{
                                        cursor: "pointer",
                                        transition: "all 0.3s ease",
                                        borderRadius: "15px",
                                        overflow: "hidden"
                                    }}
                                >
                                    <div className="position-relative overflow-hidden">
                                        <img 
                                            className="card-img-top" 
                                            src={terapia.image} 
                                            alt={terapia.title}
                                            style={{
                                                height: "200px",
                                                objectFit: "cover",
                                                transition: "transform 0.3s ease"
                                            }}
                                        />
                                        <div className="position-absolute top-0 left-0 w-100 h-100 d-flex align-items-center justify-content-center"
                                             style={{
                                                 background: "rgba(40, 167, 69, 0.8)",
                                                 opacity: 0,
                                                 transition: "opacity 0.3s ease"
                                             }}>
                                            <i className="fas fa-plus-circle text-white" style={{fontSize: "3rem"}}></i>
                                        </div>
                                    </div>
                                    <div className="card-body d-flex flex-column">
                                        <h5 className="card-title font-weight-bold text-success text-center mb-3">
                                            {terapia.title}
                                        </h5>
                                        <p className="card-text text-muted small flex-grow-1">
                                            {terapia.description.substring(0, 100)}...
                                        </p>
                                        <div className="text-center mt-auto">
                                            <span className="btn btn-outline-success btn-sm">Ver más detalles</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Apoyo Virtual Section */}
                    <div className="row mb-5">
                        <div className="col-12">
                            <div className="text-center mb-5">
                                <h2 className="display-4 font-weight-bold text-info mb-3">Apoyo Virtual</h2>
                                <p className="lead text-muted">Servicios de terapia online y apoyo a distancia</p>
                                <div className="bg-info mx-auto" style={{width: "80px", height: "4px", borderRadius: "2px"}}></div>
                            </div>
                        </div>
                        {getServicesByCategory("Apoyo Virtual").map(([key, terapia]) => (
                            <div key={key} className="col-lg-3 col-md-6 mb-4">
                                <div 
                                    className="card h-100 shadow-sm border-0 therapy-card" 
                                    onClick={() => openModal(key)}
                                    style={{
                                        cursor: "pointer",
                                        transition: "all 0.3s ease",
                                        borderRadius: "15px",
                                        overflow: "hidden"
                                    }}
                                >
                                    <div className="position-relative overflow-hidden">
                                        <img 
                                            className="card-img-top" 
                                            src={terapia.image} 
                                            alt={terapia.title}
                                            style={{
                                                height: "200px",
                                                objectFit: "cover",
                                                transition: "transform 0.3s ease"
                                            }}
                                        />
                                        <div className="position-absolute top-0 left-0 w-100 h-100 d-flex align-items-center justify-content-center"
                                             style={{
                                                 background: "rgba(23, 162, 184, 0.8)",
                                                 opacity: 0,
                                                 transition: "opacity 0.3s ease"
                                             }}>
                                            <i className="fas fa-laptop text-white" style={{fontSize: "3rem"}}></i>
                                        </div>
                                    </div>
                                    <div className="card-body d-flex flex-column">
                                        <h5 className="card-title font-weight-bold text-info text-center mb-3">
                                            {terapia.title}
                                        </h5>
                                        <p className="card-text text-muted small flex-grow-1">
                                            {terapia.description.substring(0, 100)}...
                                        </p>
                                        <div className="text-center mt-auto">
                                            <span className="btn btn-outline-info btn-sm">Ver más detalles</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>

                    {/* Material Concreto Section */}
                    <div className="row mb-5">
                        <div className="col-12">
                            <div className="text-center mb-5">
                                <h2 className="display-4 font-weight-bold text-warning mb-3">Material Concreto</h2>
                                <p className="lead text-muted">Recursos didácticos y material especializado</p>
                                <div className="bg-warning mx-auto" style={{width: "80px", height: "4px", borderRadius: "2px"}}></div>
                            </div>
                        </div>
                        {getServicesByCategory("Material Concreto").map(([key, terapia]) => (
                            <div key={key} className="col-lg-3 col-md-6 mb-4">
                                <div 
                                    className="card h-100 shadow-sm border-0 therapy-card" 
                                    onClick={() => openModal(key)}
                                    style={{
                                        cursor: "pointer",
                                        transition: "all 0.3s ease",
                                        borderRadius: "15px",
                                        overflow: "hidden"
                                    }}
                                >
                                    <div className="position-relative overflow-hidden">
                                        <img 
                                            className="card-img-top" 
                                            src={terapia.image} 
                                            alt={terapia.title}
                                            style={{
                                                height: "200px",
                                                objectFit: "cover",
                                                transition: "transform 0.3s ease"
                                            }}
                                        />
                                        <div className="position-absolute top-0 left-0 w-100 h-100 d-flex align-items-center justify-content-center"
                                             style={{
                                                 background: "rgba(255, 193, 7, 0.8)",
                                                 opacity: 0,
                                                 transition: "opacity 0.3s ease"
                                             }}>
                                            <i className="fas fa-cubes text-white" style={{fontSize: "3rem"}}></i>
                                        </div>
                                    </div>
                                    <div className="card-body d-flex flex-column">
                                        <h5 className="card-title font-weight-bold text-warning text-center mb-3">
                                            {terapia.title}
                                        </h5>
                                        <p className="card-text text-muted small flex-grow-1">
                                            {terapia.description.substring(0, 100)}...
                                        </p>
                                        <div className="text-center mt-auto">
                                            <span className="btn btn-outline-warning btn-sm">Ver más detalles</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* InfoModal Component */}
            <InfoModal
                isOpen={isModalOpen}
                onRequestClose={closeModal}
                selectedTerapia={selectedTerapia}
            />

            <style jsx>{`
                .therapy-card:hover {
                    transform: translateY(-10px);
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1) !important;
                }
                
                .therapy-card:hover img {
                    transform: scale(1.05);
                }
                
                .therapy-card:hover .position-absolute {
                    opacity: 1 !important;
                }
                
                .page-header::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="10" cy="10" r="1" fill="white" opacity="0.1"/><circle cx="90" cy="90" r="1" fill="white" opacity="0.1"/><circle cx="50" cy="30" r="0.5" fill="white" opacity="0.1"/></svg>');
                    animation: float 20s ease-in-out infinite;
                }
                
                @keyframes float {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-20px); }
                }
            `}</style>
        </>
    );
};

export default ServicesContent;