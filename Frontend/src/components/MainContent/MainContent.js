import React, { useEffect, useState } from "react";
import $ from "jquery";
import 'owl.carousel';
import Slider from "react-slick";
import InfoModal from '../Modals/InfoModal';
import Modal from '../Modals/Modal';
import "slick-carousel/slick/slick.css";
import "slick-carousel/slick/slick-theme.css";
import ContactContent from "./ContactContent";
import emailjs from "@emailjs/browser";


const MainContent = ({ toggleModal }) => {
    const [selectedTerapia, setSelectedTerapia] = useState(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [formData, setFormData] = useState({

        name: "",

        email: "",

        subject: "",

    });


    const [message, setMessage] = useState("");

    const [errors, setErrors] = useState({});


    const handleInputChange = (e) => {

        setFormData({

            ...formData,

            [e.target.name]: e.target.value,

        });

    };


    const validate = () => {

        let tempErrors = {};

        if (!formData.name) tempErrors.name = "Por favor ingrese su nombre.";

        if (!formData.email) {

            tempErrors.email = "Por favor ingrese su correo.";

        } else if (!/\S+@\S+\.\S+/.test(formData.email)) {

            tempErrors.email = "Por favor ingrese un correo válido.";

        }

        if (!formData.subject) tempErrors.subject = "Por favor ingrese el sujeto.";

        setErrors(tempErrors);

        return Object.keys(tempErrors).length === 0;

    };


    const sendEmail = (e) => {

        e.preventDefault(); // Evita el comportamiento por defecto del formulario


        if (!validate()) return; // Valida antes de enviar


        // Parámetros para el administrador

        const adminTemplateParams = {

            user_name: formData.name,

            user_email: formData.email,

            subject: formData.subject,

            to_email: "informes@centrojuanpabloii.com",

        };


        // Parámetros para el usuario

        const userTemplateParams = {

            user_name: formData.name,

            user_email: formData.email,

            reply_to: "informes@centrojuanpabloii.com",

            message: "Gracias por contactarnos. Hemos recibido tu mensaje y lo revisaremos pronto.",

        };


        // Enviar correo al administrador

        emailjs

            .send(

                "service_olcgbip", // ID del servicio

                "template_trm57wu", // ID de la plantilla para el admin

                adminTemplateParams,

                "FOH1RobDyzI3oW_rY" // ID público del usuario

            )

            .then(

                (response) => {

                    console.log("Correo enviado al administrador", response.status, response.text);


                    // Enviar correo de respuesta al usuario

                    emailjs

                        .send(

                            "service_olcgbip", // ID del servicio

                            "template_wf1pe58", // ID de la plantilla para el usuario

                            userTemplateParams,

                            "FOH1RobDyzI3oW_rY"

                        )

                        .then(

                            (userResponse) => {

                                console.log("Correo enviado al usuario", userResponse.status, userResponse.text);

                                setMessage("¡Correo enviado con éxito! Pronto nos comunicaremos contigo.");

                                setFormData({ name: "", email: "", subject: "" }); // Restablecer el formulario

                            },

                            (err) => {

                                console.error("Error al enviar correo al usuario", err);

                                setMessage("Hubo un error al enviar el correo de confirmación.");

                            }

                        );

                },

                (err) => {

                    console.error("Error al enviar correo al administrador", err);

                    setMessage("Hubo un error al enviar el correo. Inténtalo más tarde.");

                }

            );
    };
    const terapiasInfo = {
        lectoEscritura: {
            title: "LECTO-ESCRITURA",
            image: "https://th.bing.com/th/id/OIG4.Lx0DI4cJvITiZ.MhyBou?pid=ImgGn",
            description: "En esta terapia, trabajamos para potenciar las habilidades de lectura y escritura de los niños, utilizando métodos innovadores y personalizados que nos permiten alcanzar grandes logros.",
        },
        conductal: {
            title: "CONDUCTAL",
            image: "https://th.bing.com/th/id/OIG1.3rx.KXoMCiGOUzV9cq5W?pid=ImgGn",
            description: "En el Centro de Terapias Juan Pablo II, ofrecemos terapia de conducta integral para tratar problemas como agresividad, impulsividad, ansiedad y depresión. Nuestro enfoque ayuda a mejorar la calidad de vida, comenzando con la modificación de conductas, clave para el bienestar y desarrollo personal de niños, adolescentes y adultos.",
        },
        lenguaje: {
            title: "DE LENGUAJE",
            image: "https://th.bing.com/th/id/OIG2.QuFUsnwlkYLs3vu.qUB6?pid=ImgGn",
            description: "Es un proceso que se enfoca en ayudar a aquellas personas que enfrentan dificultades para hablar y sus consecuencias como  entender, leer o escribir.  A través e técnicas personalizadas, el “Centro de Terapias Juan Pablo II” soluciona problemas como la articulación incorrecta, el retraso en el desarrollo del habla, y dificultades en la comprensión y producción del lenguaje. El objetivo es facilitar una comunicación efectiva, que permita a cada persona desarrollarse plenamente en su entorno. con dificultades de habla y lenguaje.",
        },
        // Agrega más terapias aquí
        ocupacional: {
            title: "OCUPACIONAL",
            image: "https://th.bing.com/th/id/OIG3.FUFQGAdUlCUv63tDareQ?pid=ImgGn",
            description: "La terapia ocupacional se enfoca en ayudar a las personas a superar dificultades en actividades cotidianas esenciales como la alimentación, la higiene personal, el control de esfínteres, el estudio y la recreación.  En el Centro de Terapias Juan Pablo II, ofrecemos intervenciones personalizadas para fomentar la autosuficiencia y mejorar la calidad de vida de cada paciente, ayudándolos a desarrollarse plenamente en su entorno.",
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

    const TestimonialCarousel = () => {
        const settings = {
            dots: true,
            infinite: true,
            speed: 500,
            slidesToShow: 1,
            slidesToScroll: 1,
            autoplay: true,
            autoplaySpeed: 3000,
            arrows: false,
        };

        const testimonials = [
            {
                quote: "Dolor eirmod diam stet kasd sed. Aliqu rebum est eos. Rebum elitr dolore et eos labore, stet justo sed est sed. Diam sed sed dolor stet amet eirmod eos labore diam.",
                img: "img/testimonial-1.jpg",
                name: "Client Name",
                profession: "Profession",
            },
            {
                quote: "Dolor eirmod diam stet kasd sed. Aliqu rebum est eos. Rebum elitr dolore et eos labore, stet justo sed est sed. Diam sed sed dolor stet amet eirmod eos labore diam.",
                img: "img/testimonial-2.jpg",
                name: "Client Name",
                profession: "Profession",
            },
            {
                quote: "Dolor eirmod diam stet kasd sed. Aliqu rebum est eos. Rebum elitr dolore et eos labore, stet justo sed est sed. Diam sed sed dolor stet amet eirmod eos labore diam.",
                img: "img/testimonial-3.jpg",
                name: "Client Name",
                profession: "Profession",
            },
        ];

        return (
            <Slider {...settings}>
                {testimonials.map((testimonial, index) => (
                    <div key={index} className="text-center">
                        <i className="fa fa-3x fa-quote-left text-primary mb-4"></i>
                        <h4 className="font-weight-normal mb-4">{testimonial.quote}</h4>
                        <img className="img-fluid mx-auto mb-3" src={testimonial.img} alt={testimonial.name} />
                        <h5 className="m-0">{testimonial.name}</h5>
                        <span>{testimonial.profession}</span>
                    </div>))}
            </Slider>
        );
    };

    return (
        <main>
            <div className="container-fluid p-0 pb-5 mb-5 pt-2">
                <div id="header-carousel" className="carousel slide carousel-fade" data-ride="carousel">
                    <ol className="carousel-indicators">
                        <li data-target="#header-carousel" data-slide-to="0" className="active"></li>
                        <li data-target="#header-carousel" data-slide-to="1"></li>
                        <li data-target="#header-carousel" data-slide-to="2"></li>
                    </ol>
                    <div className="carousel-inner">
                        <div className="carousel-item active" style={{ minHeight: "300px", maxHeight: "30%" }}>
                            <img className="position-relative w-100" src="https://th.bing.com/th/id/OIG2..wGinq22WgqTmh29J6hr?pid=ImgGn" style={{ minHeight: "100px", objectFit: "cover" }} />
                            <div className="carousel-caption d-flex align-items-center justify-content-center">
                                <div className="p-5" style={{ width: "100%", maxWidth: "900px", maxHeight: "40%" }}>
                                    <h5 className="text-white text-uppercase mb-md-3">SEGUIMOS EN VERANO CON TERAPIAS DE:</h5>
                                    <h1 className="display-3 text-white mb-md-4">LECTO-ESCRITURA</h1>
                                    <button
                                        className="btn btn-primary py-md-2 px-md-4 font-weight-semi-bold mt-2"
                                        onClick={scrollToSection}
                                    >
                                        Más Info
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="carousel-item" style={{ minHeight: "300px", maxHeight: "30%" }}>
                            <img className="position-relative w-100" src="https://th.bing.com/th/id/OIG3.3YWycEyA7d3DuqRvtO_y?pid=ImgGn" style={{ minHeight: "300px", objectFit: "cover" }} />
                            <div className="carousel-caption d-flex align-items-center justify-content-center">
                                <div className="p-5" style={{ width: "100%", maxWidth: "900px", maxHeight: "40%" }}>
                                    <h5 className="text-white text-uppercase mb-md-3">SEGUIMOS EN VERANO CON TERAPIAS DE:</h5>
                                    <h1 className="display-3 text-white mb-md-4">CONDUCTAL</h1>
                                    <button
                                        className="btn btn-primary py-md-2 px-md-4 font-weight-semi-bold mt-2"
                                        onClick={scrollToSection}
                                    >
                                        Más Info
                                    </button>
                                </div>
                            </div>
                        </div>
                        <div className="carousel-item" style={{ minHeight: "300px" }}>
                            <img className="position-relative w-100" src="https://th.bing.com/th/id/OIG1.tZNMX5miyC83itLxq1Rb?w=1024&h=1024&rs=1&pid=ImgDetMain" style={{ minHeight: "300px", objectFit: "cover" }} />
                            <div className="carousel-caption d-flex align-items-center justify-content-center">
                                <div className="p-5" style={{ width: "100%", maxWidth: "900px", maxHeight: "40%" }}>
                                    <h5 className="text-white text-uppercase mb-md-3">SEGUIMOS EN VERANO CON TERAPIAS DE:</h5>
                                    <h1 className="display-3 text-white mb-md-4">DE LENGUAJE</h1>
                                    <button
                                        className="btn btn-primary py-md-2 px-md-4 font-weight-semi-bold mt-2"
                                        onClick={scrollToSection}
                                    >
                                        Más Info
                                    </button>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>
            </div>

            <div className="container-fluid py-5">
                <div className="container py-5">
                    <div className="row align-items-center">
                        <div className="col-lg-5">
                            <img className="img-fluid rounded mb-4 mb-lg-0" src="https://th.bing.com/th/id/OIG2.EGnJUX_Eupo9pPH.THj5?pid =ImgGn" alt="" />
                        </div>
                        <div className="col-lg-7">
                            <div className="text-left mb-4 ">
                                <h5 className="text-primary text-uppercase mb-3 text-center" style={{ letterSpacing: "5px" }}>Acerca de nosotros</h5>
                                <h1 className="text-center">Innovadora Forma de Aprender</h1>
                            </div>
                            <p className="text-center"> En el Centro de Terapias Juan Pablo II, trabajamos para potenciar el aprendizaje y el desarrollo integral de las personas. Nuestro objetivo es estimular y fortalecer las capacidades cognitivas, brindando herramientas que promuevan un crecimiento personal y académico. A través de un enfoque personalizado, buscamos que cada individuo alcance su máximo potencial, mejorando su calidad de vida y su bienestar emocional.</p>
                            <button

                                className="btn btn-primary py-md-2 px-md-4 font-weight-semi-bold mt-2"

                                onClick={openModal}

                            >

                                Más Info

                            </button>

                            <Modal isOpen={isModalOpen} toggleModal={closeModal} />
                        </div>
                    </div>
                </div>
            </div>

            <div className="container-fluid py-5">
                <div className="container pt-5 pb-3">
                    <div className="text-center mb-5" id="terapias">
                        <h5 className="text-primary text-uppercase mb-3" style={{ letterSpacing: "5px" }}>TERAPIAS</h5>
                        <h1>Explora las Distintas Terapias</h1>
                    </div>
                    <div className="row align-items-center">
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('lectoEscritura')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.lectoEscritura.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.lectoEscritura.title}</h4>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('conductal')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.conductal.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.conductal.title}</h4>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('lenguaje')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.lenguaje.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.lenguaje.title}</h4>
                                </div>
                            </div>
                        </div>
                        {/* Agrega más tarjetas de terapia aquí */}
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('ocupacional')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.ocupacional.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.ocupacional.title}</h4>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('aprendizaje')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.aprendizaje.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.aprendizaje.title}</h4>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('autismo')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.autismo.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.autismo.title}</h4>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('down')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.down.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.down.title}</h4>
                                </div>
                            </div>
                        </div>
                        <div className="col-lg-3 col-md-6 mb-4" onClick={() => openModal('intelectual')}>
                            <div className="cat-item position-relative overflow-hidden rounded mb-2">
                                <img className="img-fluid" src={terapiasInfo.intelectual.image} alt="" />
                                <div className="cat-overlay text-white text-decoration-none">
                                    <h4 className="text-white font-weight-medium">{terapiasInfo.intelectual.title}</h4>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container-fluid bg-registration py-5" style={{ margin: "90px 0" }}>
                <div className="container py-5">
                    <div className="row align-items-center">
                        <div className="col-lg-7 mb-5 mb-lg-0">
                            <div className="mb-4">
                                <h5 className="text-primary text-uppercase mb-3" style={{ letterSpacing: "5px" }}>Deseas Inscribirte?</h5>
                                <h1 className="text-white">30% de descuento en la evaluación inicial</h1>
                            </div>
                            <p className="text-white">Ingrese su nombre, dirección de correo electrónico y selecciona en qué deseas recibir información y nos contactaremos con usted</p>
                            <ul className="list-inline text-white m-0">
                                <li className="py-2"><i className="fa fa-check text-primary mr-3"></i>Datos Seguros</li>
                                <li className="py-2"><i className="fa fa-check text-primary mr-3"></i>Interacción personal y segura</li>
                                <li className="py-2"><i className="fa fa-check text-primary mr-3"></i>Comunicación Directa</li>

                            </ul>
                        </div>
                        <div className="col-lg-5">
                            <div className="card border-0">
                                <div className="card-header bg-light text-center p-4">
                                    <h1 className="m-0">Date a conocer!</h1>
                                </div>
                                <div className="card-body rounded-bottom bg-primary p-5">

                                    <form onSubmit={sendEmail}>

                                        <div className="form-group">

                                            <input

                                                type="text"

                                                name="name" // Asegúrate de que no haya espacios

                                                className={`form-control border-0 p-4 ${errors.name ? "is-invalid" : ""}`}

                                                placeholder="Ingrese su nombre"

                                                required="required"

                                                value={formData.name}

                                                onChange={handleInputChange}

                                            />

                                        </div>

                                        <div className="form-group">

                                            <input

                                                type="email"

                                                name="email"

                                                className={`form-control border-0 p-4 ${errors.email ? "is-invalid" : ""}`}

                                                placeholder="Ingrese su correo"

                                                required="required"

                                                value={formData.email}

                                                onChange={handleInputChange}

                                            />

                                        </div>

                                        <div className="form-group">

                                            <select

                                                className={`form-control border-0 p -4 ${errors.subject ? "is-invalid" : ""}`}

                                                style={{ height: "47px" }}

                                                name="subject"

                                                value={formData.subject}

                                                onChange={handleInputChange}

                                            >

                                                <option value="">Seleccione un servicio</option>

                                                <option value="1">Terapias</option>

                                                <option value="2">Terapias Integrales</option>

                                                <option value="3">Material Virtual</option>

                                                <option value="4">Material Físico</option>

                                            </select>

                                        </div>

                                        <div>

                                            <button className="btn btn-dark btn-block border-0 py-3" type="submit">Enviar</button>

                                        </div>

                                    </form>

                                    {message && <p className="text-center mt-3">{message}</p>}

                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div className="container-fluid py-5">
                <div className="row justify-content-center">
                    <div className="col-lg-8">
                        <TestimonialCarousel />
                    </div>
                </div>
            </div>
            <InfoModal
                isOpen={isModalOpen}
                onRequestClose={closeModal}
                selectedTerapia={selectedTerapia}
            />

        </main>
    );
};

export default MainContent;// Asegúrate de que la ruta sea correcta