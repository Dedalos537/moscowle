import React, { useEffect, useState } from "react";

const ServicesContent = () => {
    const [selectedTerapia, setSelectedTerapia] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const terapiasInfo = {
        lectoEscritura: {
            title: "LECTO-ESCRITURA",
            image: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=300&fit=crop&crop=center",
            description: "En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños, utilizando métodos innovadores y personalizados que nos permiten alcanzar grandes logros.",
            category: "Terapias",
            icon: "📚"
        },
        conductual: {
            title: "CONDUCTUAL",
            image: "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=300&fit=crop&crop=center",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad, impulsividad, ansiedad y depresión. Nuestro enfoque ayuda a mejorar la calidad de vida, comenzando con la modificación de conductas, clave para el bienestar y desarrollo personal de niños, adolescentes y adultos.",
            category: "Terapias",
            icon: "🧠"
        },
        lenguaje: {
            title: "DE LENGUAJE",
            image: "https://images.unsplash.com/photo-1576267423445-b2e0074d68a4?w=400&h=300&fit=crop&crop=center",
            description: "Es un proceso que se enfoca en ayudar a aquellas personas que enfrentan dificultades para hablar y sus consecuencias como entender, leer o escribir. A través de técnicas personalizadas, el Centro de Terapias Juan Pablo II soluciona problemas como la articulación incorrecta, el retraso en el desarrollo del habla, y dificultades en la comprensión y producción del lenguaje.",
            category: "Terapias",
            icon: "🗣️"
        },
        aprendizaje: {
            title: "DE APRENDIZAJE",
            image: "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=400&h=300&fit=crop&crop=center",
            description: "Terapia especializada en superar dificultades de aprendizaje, utilizando técnicas personalizadas para mejorar el rendimiento académico y las habilidades cognitivas de cada paciente.",
            category: "Terapias",
            icon: "🎓"
        },
        ocupacional: {
            title: "OCUPACIONAL",
            image: "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=400&h=300&fit=crop&crop=center",
            description: "La terapia ocupacional se enfoca en ayudar a las personas a superar dificultades en actividades cotidianas esenciales como la alimentación, la higiene personal, el control de esfínteres, el estudio y la recreación. En el Centro de Terapias Juan Pablo II, ofrecemos intervenciones personalizadas para fomentar la autosuficiencia y mejorar la calidad de vida de cada paciente.",
            category: "Terapias",
            icon: "🏠"
        },
        autismo: {
            title: "AUTISMO (TEA)",
            image: "https://images.unsplash.com/photo-1587654780291-39c9404d746b?w=400&h=300&fit=crop&crop=center",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Trastorno del Espectro Autista (TEA). Utilizamos técnicas propias para ayudar a mejorar la comunicación, la interacción social y la adaptación al entorno.",
            category: "Terapias Integrales",
            icon: "🌈"
        },
        tda: {
            title: "TDA",
            image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop&crop=center",
            description: "Tratamiento especializado para el Trastorno por Déficit de Atención, enfocado en mejorar la concentración, organización y habilidades ejecutivas a través de técnicas terapéuticas personalizadas.",
            category: "Terapias Integrales",
            icon: "🎯"
        },
        tdah: {
            title: "TDAH",
            image: "https://images.unsplash.com/photo-1551601651-2a8555f1a136?w=400&h=300&fit=crop&crop=center",
            description: "Abordaje integral del Trastorno por Déficit de Atención e Hiperactividad, combinando estrategias conductuales y cognitivas para mejorar el autocontrol, la atención y las habilidades sociales.",
            category: "Terapias Integrales",
            icon: "⚡"
        },
        down: {
            title: "SÍNDROME DE DOWN",
            image: "https://images.unsplash.com/photo-1544027993-37dbfe43562a?w=400&h=300&fit=crop&crop=center",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Síndrome de Down. Utilizamos técnicas propias para mejorar el desarrollo psicomotor, el lenguaje y la autonomía personal.",
            category: "Terapias Integrales",
            icon: "💙"
        },
        intelectual: {
            title: "DISCAPACIDAD INTELECTUAL",
            image: "https://images.unsplash.com/photo-1609081219090-a6d81d3085bf?w=400&h=300&fit=crop&crop=center",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos apoyo especializado para personas con Discapacidad Intelectual. Utilizamos técnicas propias para fortalecer las habilidades cognitivas, la comunicación y la independencia funcional.",
            category: "Terapias Integrales",
            icon: "🧩"
        },
        comunicacionOral: {
            title: "COMUNICACIÓN ORAL",
            image: "https://images.unsplash.com/photo-1577563908411-5077b6dc7624?w=400&h=300&fit=crop&crop=center",
            description: "Apoyo virtual especializado en el desarrollo de habilidades de comunicación oral, utilizando herramientas digitales innovadoras para mejorar la expresión verbal y la comprensión auditiva.",
            category: "Apoyo Virtual",
            icon: "💻"
        },
        lectoEscrituraVirtual: {
            title: "LECTO-ESCRITURA VIRTUAL",
            image: "https://images.unsplash.com/photo-1513475382585-d06e58bcb0e0?w=400&h=300&fit=crop&crop=center",
            description: "Programa virtual de apoyo en lectoescritura, diseñado para fortalecer las habilidades de lectura y escritura a través de plataformas digitales interactivas.",
            category: "Apoyo Virtual",
            icon: "📖"
        },
        matematicas: {
            title: "MATEMÁTICAS",
            image: "https://images.unsplash.com/photo-1509228468518-180dd4864904?w=400&h=300&fit=crop&crop=center",
            description: "Apoyo virtual en matemáticas que utiliza metodologías digitales para facilitar el aprendizaje de conceptos numéricos y operaciones matemáticas básicas y avanzadas.",
            category: "Apoyo Virtual",
            icon: "🔢"
        },
        desarrolloCognitivo: {
            title: "DESARROLLO COGNITIVO",
            image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop&crop=center",
            description: "Programa virtual enfocado en estimular y desarrollar las funciones cognitivas superiores como memoria, atención, percepción y funciones ejecutivas.",
            category: "Apoyo Virtual",
            icon: "🧠"
        }
    };

    const materialConcreto = {
        comunicacionOralMaterial: {
            title: "COMUNICACIÓN ORAL",
            image: "https://images.unsplash.com/photo-1596464716127-f2a82984de30?w=400&h=300&fit=crop&crop=center",
            description: "Material concreto diseñado para estimular y desarrollar las habilidades de comunicación oral a través de juegos, tarjetas y actividades interactivas.",
            category: "Material Concreto",
            icon: "🎲"
        },
        lectoEscrituraMaterial: {
            title: "LECTO-ESCRITURA",
            image: "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=400&h=300&fit=crop&crop=center",
            description: "Recursos tangibles y manipulativos para el aprendizaje de la lectura y escritura, incluyendo letras móviles, libros sensoriales y material didáctico especializado.",
            category: "Material Concreto",
            icon: "🔤"
        },
        matematicasMaterial: {
            title: "MATEMÁTICAS",
            image: "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=400&h=300&fit=crop&crop=center",
            description: "Material manipulativo para el aprendizaje de conceptos matemáticos, incluyendo ábacos, bloques lógicos, regletas y otros recursos didácticos concretos.",
            category: "Material Concreto",
            icon: "🧮"
        },
        desarrolloCognitivoMaterial: {
            title: "DESARROLLO COGNITIVO",
            image: "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?w=400&h=300&fit=crop&crop=center",
            description: "Recursos físicos y tangibles diseñados para estimular el desarrollo cognitivo, incluyendo rompecabezas, juegos de memoria y material sensorial especializado.",
            category: "Material Concreto",
            icon: "🧩"
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

    const getServicesByCategory = (category) => {
        return Object.entries(allServices).filter(([key, service]) => service.category === category);
    };

    const getCategoryColor = (category) => {
        switch (category) {
            case "Terapias": return { primary: "#667eea", secondary: "#764ba2" };
            case "Terapias Integrales": return { primary: "#28a745", secondary: "#20c997" };
            case "Apoyo Virtual": return { primary: "#17a2b8", secondary: "#6f42c1" };
            case "Material Concreto": return { primary: "#ffc107", secondary: "#fd7e14" };
            default: return { primary: "#667eea", secondary: "#764ba2" };
        }
    };

    const ServiceCard = ({ service, serviceKey, category }) => {
        const colors = getCategoryColor(category);

        return (
            <div className="col-lg-3 col-md-6 col-sm-6 mb-4">
                <div
                    className="service-card h-100"
                    onClick={() => openModal(serviceKey)}
                    style={{
                        cursor: "pointer",
                        borderRadius: "20px",
                        overflow: "hidden",
                        background: "white",
                        boxShadow: "0 10px 30px rgba(0,0,0,0.1)",
                        transition: "all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1)",
                        border: "none",
                        position: "relative"
                    }}
                >
                    {/* Image Section */}
                    <div
                        className="card-image-container"
                        style={{
                            height: "200px",
                            position: "relative",
                            overflow: "hidden",
                            background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`
                        }}
                    >
                        <img
                            src={service.image}
                            alt={service.title}
                            style={{
                                width: "100%",
                                height: "100%",
                                objectFit: "cover",
                                transition: "transform 0.4s ease",
                                opacity: "0.9"
                            }}
                            onError={(e) => {
                                e.target.style.display = 'none';
                            }}
                        />
                        <div
                            className="overlay"
                            style={{
                                position: "absolute",
                                top: 0,
                                left: 0,
                                right: 0,
                                bottom: 0,
                                background: `linear-gradient(135deg, ${colors.primary}dd, ${colors.secondary}dd)`,
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                opacity: 0,
                                transition: "opacity 0.3s ease"
                            }}
                        >
                            <div style={{ fontSize: "3rem" }}>{service.icon}</div>
                        </div>

                        {/* Icon Badge */}
                        <div
                            style={{
                                position: "absolute",
                                top: "15px",
                                right: "15px",
                                background: "rgba(255,255,255,0.9)",
                                borderRadius: "50%",
                                width: "50px",
                                height: "50px",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                fontSize: "1.5rem",
                                boxShadow: "0 4px 12px rgba(0,0,0,0.15)"
                            }}
                        >
                            {service.icon}
                        </div>
                    </div>

                    {/* Content Section */}
                    <div
                        className="card-body"
                        style={{
                            padding: "25px 20px",
                            display: "flex",
                            flexDirection: "column",
                            minHeight: "180px"
                        }}
                    >
                        <h5
                            style={{
                                fontWeight: "700",
                                fontSize: "1.1rem",
                                color: colors.primary,
                                textAlign: "center",
                                marginBottom: "15px",
                                lineHeight: "1.3",
                                textTransform: "uppercase",
                                letterSpacing: "0.5px"
                            }}
                        >
                            {service.title}
                        </h5>

                        <p
                            style={{
                                color: "#6c757d",
                                fontSize: "0.9rem",
                                lineHeight: "1.6",
                                flexGrow: 1,
                                marginBottom: "20px",
                                textAlign: "justify"
                            }}
                        >
                            {service.description.length > 120
                                ? service.description.substring(0, 120) + "..."
                                : service.description}
                        </p>

                        <div style={{ textAlign: "center" }}>
                            <button
                                style={{
                                    background: `linear-gradient(135deg, ${colors.primary}, ${colors.secondary})`,
                                    color: "white",
                                    border: "none",
                                    borderRadius: "25px",
                                    padding: "10px 25px",
                                    fontSize: "0.85rem",
                                    fontWeight: "600",
                                    textTransform: "uppercase",
                                    letterSpacing: "0.5px",
                                    transition: "all 0.3s ease",
                                    cursor: "pointer"
                                }}
                            >
                                Ver detalles
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    return (
        <div style={{ fontFamily: "Arial, sans-serif" }}>
            {/* Header Section */}
            <div
                className="container-fluid page-header mb-5"
                style={{
                    padding: "100px 0",
                    marginBottom: "60px",
                    position: "relative",
                    overflow: "hidden"
                }}
            >
                <div
                    style={{
                        position: "absolute",
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        animation: "float 20s ease-in-out infinite"
                    }}
                />

                <div className="container" style={{ position: "relative", zIndex: 2, textAlign: "center" }}>
                    <h1
                        style={{
                            fontSize: "3.5rem",
                            fontWeight: "800",
                            color: "white",
                            marginBottom: "20px",
                            textShadow: "2px 2px 4px rgba(0,0,0,0.3)"
                        }}
                    >
                        Nuestros Servicios
                    </h1>

                    <div style={{ color: "rgba(255,255,255,0.8)", fontSize: "1rem" }}>
                        <span>Inicio</span>
                        <span style={{ margin: "0 15px" }}>»</span>
                        <span>Servicios</span>
                    </div>
                </div>
            </div>

            {/* Services Content */}
            <div className="container" style={{ padding: "0 15px" }}>

                {/* Terapias Integrales Section */}
                <div style={{ marginBottom: "80px" }}>
                    <div style={{ textAlign: "center", marginBottom: "50px" }}>
                        <h2
                            style={{
                                fontSize: "2.8rem",
                                fontWeight: "700",
                                color: "#28a745",
                                marginBottom: "15px"
                            }}
                        >
                            Terapias Integrales
                        </h2>
                        <p
                            style={{
                                fontSize: "1.1rem",
                                color: "#6c757d",
                                marginBottom: "25px"
                            }}
                        >
                            Programas especializados para condiciones específicas
                        </p>
                        <div
                            style={{
                                width: "80px",
                                height: "4px",
                                background: "linear-gradient(135deg, #28a745, #20c997)",
                                margin: "0 auto",
                                borderRadius: "2px"
                            }}
                        />
                    </div>
                    <div className="row">
                        {getServicesByCategory("Terapias Integrales").map(([key, service]) => (
                            <ServiceCard key={key} service={service} serviceKey={key} category="Terapias Integrales" />
                        ))}
                    </div>
                </div>

                {/* Terapias Section */}
                <div style={{ marginBottom: "80px" }}>
                    <div style={{ textAlign: "center", marginBottom: "50px" }}>
                        <h2
                            style={{
                                fontSize: "2.8rem",
                                fontWeight: "700",
                                color: "#667eea",
                                marginBottom: "15px"
                            }}
                        >
                            Terapias Especializadas
                        </h2>
                        <p
                            style={{
                                fontSize: "1.1rem",
                                color: "#6c757d",
                                marginBottom: "25px"
                            }}
                        >
                            Terapias individualizadas para el desarrollo de habilidades específicas
                        </p>
                        <div
                            style={{
                                width: "80px",
                                height: "4px",
                                background: "linear-gradient(135deg, #667eea, #764ba2)",
                                margin: "0 auto",
                                borderRadius: "2px"
                            }}
                        />
                    </div>
                    <div className="row">
                        {getServicesByCategory("Terapias").map(([key, service]) => (
                            <ServiceCard key={key} service={service} serviceKey={key} category="Terapias" />
                        ))}
                    </div>
                </div>



                {/* Apoyo Virtual Section */}
                <div style={{ marginBottom: "80px" }}>
                    <div style={{ textAlign: "center", marginBottom: "50px" }}>
                        <h2
                            style={{
                                fontSize: "2.8rem",
                                fontWeight: "700",
                                color: "#17a2b8",
                                marginBottom: "15px"
                            }}
                        >
                            Apoyo Virtual
                        </h2>
                        <p
                            style={{
                                fontSize: "1.1rem",
                                color: "#6c757d",
                                marginBottom: "25px"
                            }}
                        >
                            Servicios de terapia online y apoyo a distancia
                        </p>
                        <div
                            style={{
                                width: "80px",
                                height: "4px",
                                background: "linear-gradient(135deg, #17a2b8, #6f42c1)",
                                margin: "0 auto",
                                borderRadius: "2px"
                            }}
                        />
                    </div>
                    <div className="row">
                        {getServicesByCategory("Apoyo Virtual").map(([key, service]) => (
                            <ServiceCard key={key} service={service} serviceKey={key} category="Apoyo Virtual" />
                        ))}
                    </div>
                </div>

                {/* Material Concreto Section */}
                <div style={{ marginBottom: "80px" }}>
                    <div style={{ textAlign: "center", marginBottom: "50px" }}>
                        <h2
                            style={{
                                fontSize: "2.8rem",
                                fontWeight: "700",
                                color: "#ffc107",
                                marginBottom: "15px"
                            }}
                        >
                            Material Concreto
                        </h2>
                        <p
                            style={{
                                fontSize: "1.1rem",
                                color: "#6c757d",
                                marginBottom: "25px"
                            }}
                        >
                            Recursos didácticos y material especializado
                        </p>
                        <div
                            style={{
                                width: "80px",
                                height: "4px",
                                background: "linear-gradient(135deg, #ffc107, #fd7e14)",
                                margin: "0 auto",
                                borderRadius: "2px"
                            }}
                        />
                    </div>
                    <div className="row">
                        {getServicesByCategory("Material Concreto").map(([key, service]) => (
                            <ServiceCard key={key} service={service} serviceKey={key} category="Material Concreto" />
                        ))}
                    </div>
                </div>
            </div>

            {/* Modal Simple */}
            {isModalOpen && selectedTerapia && (
                <div
                    style={{
                        position: "fixed",
                        top: 0,
                        left: 0,
                        width: "100%",
                        height: "100%",
                        background: "rgba(0,0,0,0.8)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        zIndex: 1000,
                        padding: "20px"
                    }}
                    onClick={closeModal}
                >
                    <div
                        style={{
                            background: "white",
                            borderRadius: "20px",
                            padding: "40px",
                            maxWidth: "600px",
                            width: "100%",
                            maxHeight: "80vh",
                            overflow: "auto",
                            position: "relative"
                        }}
                        onClick={(e) => e.stopPropagation()}
                    >
                        <button
                            onClick={closeModal}
                            style={{
                                position: "absolute",
                                top: "15px",
                                right: "20px",
                                background: "none",
                                border: "none",
                                fontSize: "2rem",
                                cursor: "pointer",
                                color: "#999"
                            }}
                        >
                            ×
                        </button>

                        <div style={{ textAlign: "center", marginBottom: "30px" }}>
                            <div style={{ fontSize: "4rem", marginBottom: "20px" }}>
                                {selectedTerapia.icon}
                            </div>
                            <h2 style={{
                                color: getCategoryColor(selectedTerapia.category).primary,
                                fontSize: "2rem",
                                fontWeight: "700",
                                marginBottom: "20px"
                            }}>
                                {selectedTerapia.title}
                            </h2>
                            <img
                                src={selectedTerapia.image}
                                alt={selectedTerapia.title}
                                style={{
                                    width: "100%",
                                    maxHeight: "200px",
                                    objectFit: "cover",
                                    borderRadius: "15px",
                                    marginBottom: "20px"
                                }}
                            />
                            <p style={{
                                color: "#6c757d",
                                fontSize: "1.1rem",
                                lineHeight: "1.7",
                                textAlign: "justify"
                            }}>
                                {selectedTerapia.description}
                            </p>
                        </div>
                    </div>
                </div>
            )}

            <style jsx>{`
                @keyframes float {
                    0%, 100% { transform: translateY(0px); }
                    50% { transform: translateY(-20px); }
                }
                
                .service-card:hover {
                    transform: translateY(-15px) scale(1.02);
                    box-shadow: 0 25px 50px rgba(0,0,0,0.2);
                }
                
                .service-card:hover .card-image-container img {
                    transform: scale(1.1);
                }
                
                .service-card:hover .overlay {
                    opacity: 1;
                }
                
                .service-card:hover button {
                    transform: translateY(-2px);
                    box-shadow: 0 8px 25px rgba(0,0,0,0.3);
                }
                
                .container {
                    max-width: 1200px;
                    margin: 0 auto;
                }
                
                .row {
                    display: flex;
                    flex-wrap: wrap;
                    margin: 0 -15px;
                }
                
                .col-lg-3 {
                    flex: 0 0 25%;
                    max-width: 25%;
                    padding: 0 15px;
                }
                
                .col-md-6 {
                    flex: 0 0 50%;
                    max-width: 50%;
                }
                
                .col-sm-6 {
                    flex: 0 0 50%;
                    max-width: 50%;
                }
                
                @media (max-width: 991px) {
                    .col-lg-3 {
                        flex: 0 0 50%;
                        max-width: 50%;
                    }
                }
                
                @media (max-width: 767px) {
                    .col-lg-3, .col-md-6, .col-sm-6 {
                        flex: 0 0 100%;
                        max-width: 100%;
                    }
                }
            `}</style>
        </div>
    );
};

export default ServicesContent;