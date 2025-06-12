import React, { useState, useEffect } from 'react';
import './styleLMS.css';
import './noti.css';

const CoursesComponent = ({ handleNavigation }) => {
  const [darkMode, setDarkMode] = useState(false);
  const [profileActive, setProfileActive] = useState(false);
  const [searchActive, setSearchActive] = useState(false);
  const [sideBarActive, setSideBarActive] = useState(false);
  const [notificationActive, setNotificationActive] = useState(false);
  const [calendarVisible, setCalendarVisible] = useState(false);
  const [bodyActive, setBodyActive] = useState(false);

  const enableDarkMode = () => {
    setDarkMode(true);
  };

  const disableDarkMode = () => {
    setDarkMode(false);
  };

  const toggleDarkMode = () => {
    if (darkMode) {
      disableDarkMode();
    } else {
      enableDarkMode();
    }
  };

  const toggleProfile = () => {
    setProfileActive(!profileActive);
    setSearchActive(false);
  };

  const toggleSearch = () => {
    setSearchActive(!searchActive);
    setProfileActive(false);
  };

  const toggleSideBar = () => {
    setSideBarActive(!sideBarActive);
    setBodyActive(!bodyActive);
  };

  const closeSideBar = () => {
    setSideBarActive(false);
    setBodyActive(false);
  };

  const toggleNotification = () => {
    setNotificationActive(!notificationActive);
  };

  const closeNotification = () => {
    setNotificationActive(false);
  };

  const toggleCalendar = () => {
    setCalendarVisible(!calendarVisible);
  };

  // Función para regresar al inicio
  const goBackToHome = () => {
    if (handleNavigation) {
      handleNavigation("/");
    }
  };

  // Handle window scroll and resize
  useEffect(() => {
    const handleScroll = () => {
      setProfileActive(false);
      setSearchActive(false);
      if (window.innerWidth < 1200) {
        setSideBarActive(false);
        setBodyActive(false);
      }
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  return (
    <div className={`courses-component ${darkMode ? 'dark' : ''} ${bodyActive ? 'active' : ''}`}>
      <div className="header">
        <section className="flex">
          <a href="home.html" className="logo">
            <img src="/img/logito.jpg" alt="Logo" className="logo-image" />
            <strong>
              <samp style={{ color: '#4dd282', marginRight: '4px' }}>Juan </samp> 
              Pablo II
            </strong>
          </a>

          <div className="icons">
            {/* Botón de regreso al inicio */}
            <div 
              className="fas fa-arrow-left"
              onClick={goBackToHome}
              style={{ cursor: 'pointer', marginRight: '10px', fontSize: '18px' }}
              title="Regresar al inicio"
            ></div>
            <div 
              id="search-btn" 
              className="fas fa-search"
              onClick={toggleSearch}
            ></div>
            <div 
              id="user-btn" 
              className="fas fa-user"
              onClick={toggleProfile}
            ></div>
            <div 
              id="notification-btn" 
              className="fas fa-bell" 
              style={{ cursor: 'pointer' }}
              onClick={toggleNotification}
            ></div>
            <div 
              id="calendar-btn" 
              className="fas fa-calendar" 
              style={{ cursor: 'pointer' }}
              onClick={toggleCalendar}
            ></div>
            <input 
              type="text" 
              id="calendar" 
              className="calendar" 
              style={{ display: calendarVisible ? 'block' : 'none' }} 
              readOnly 
            />
            <div 
              id="toggle-btn" 
              className={`fas ${darkMode ? 'fa-moon' : 'fa-sun'}`}
              onClick={toggleDarkMode}
            ></div>
            <div 
              id="menu-btn" 
              className="fas fa-bars"
              onClick={toggleSideBar}
            ></div>
          </div>

          <div className={`profile ${profileActive ? 'active' : ''}`}>
            <img src="/img/pic-1.jpg" className="image" alt="" />
            <h3 className="name">Lucia Martinez</h3>
            <p className="role">Estudiante</p>
            <a href="perfil.html" className="btn">Ver Perfil</a>
          </div>

          <div className={`search-form ${searchActive ? 'active' : ''}`}>
            <input type="search" placeholder="buscar aquí..." />
            <button className="fas fa-search"></button>
          </div>

          <div className={`notification-bar ${notificationActive ? 'active' : ''}`}>
            <div className="notification-header">
              <button className="back-btn" onClick={closeNotification}>
                <i className="fas fa-times"></i>
              </button>
              <h2>Notificaciones</h2>
            </div>
            <div className="notifications">
              {/* Notificación 1*/}
              <div className="notification tarea">
                <div className="notification-icon">
                  <i className="fas fa-file-alt"></i>
                </div>
                <div className="notification-content">
                  <p className="notification-course">Curso: Terapia Cognitiva</p>
                  <p className="notification-week">Sección de Desarrollo: 5</p>
                  <p className="notification-type">Tipo de Tarea: Evaluación</p>
                  <p className="notification-due">Fecha de Vencimiento: 23 oct.</p>
                </div>
              </div>
              {/* Notificación 2*/}
              <div className="notification encuesta">
                <div className="notification-icon">
                  <i className="fas fa-poll"></i>
                </div>
                <div className="notification-content">
                  <p className="notification-course">Curso: Terapia Conductual</p>
                  <p className="notification-week">Sección de Desarrollo: 3</p>
                  <p className="notification-type">Tipo de Tarea: Encuesta</p>
                  <p className="notification-due">Fecha de Vencimiento: 25 oct.</p>
                </div>
              </div>
              {/* Notificación 3*/}
              <div className="notification comentario">
                <div className="notification-icon">
                  <i className="fas fa-comments"></i>
                </div>
                <div className="notification-content">
                  <p className="notification-course">Curso: Terapia Familiar</p>
                  <p className="notification-week">Sección de Desarrollo: 2</p>
                  <p className="notification-type">Tipo de Tarea: Comentario en Foro</p>
                  <p className="notification-date">Fecha de Ingreso: 21 oct.</p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>

      <div className={`side-bar ${sideBarActive ? 'active' : ''}`}>
        <div id="close-btn" onClick={closeSideBar}>
          <i className="fas fa-times"></i>
        </div>

        <div className="profile">
          <img src="/img/pic-1.jpg" className="image" alt="" />
          <h3 className="name">Lucia Martinez</h3>
          <p className="role">Estudiante</p>
          <a href="perfil.html" className="btn">Ver Perfil</a>
        </div>

        <nav className="navbar">
          <a href="cursos.html">
            <i className="fas fa-graduation-cap"></i>
            <span>Cursos</span>
          </a>
          <a href="tarea.html">
            <i className="fas fa-file-alt"></i>
            <span>Tareas</span>
          </a>
          <a href="progreso.html">
            <i className="fas fa-chart-line"></i>
            <span>Progreso</span>
          </a>
          <a href="calendario.html">
            <i className="fas fa-calendar-alt"></i>
            <span>Calendario</span>
          </a>
          {/* Botón de regreso en el sidebar */}
          <a onClick={goBackToHome} style={{ cursor: 'pointer' }}>
            <i className="fas fa-arrow-left"></i>
            <span>Regresar al Inicio</span>
          </a>
        </nav>
      </div>

      <section className="courses">
        <h1 className="heading">Cursos</h1>

        <div className="box-container">
          {/* Generación dinámica de cursos */}
          {[
            { id: 1, tutor: '/img/pic-1.jpg', thumb: '/img/IM2.PNG' },
            { id: 2, tutor: '/img/pic-2.jpg', thumb: '/img/IM3.PNG' },
            { id: 3, tutor: '/img/pic-3.jpg', thumb: '/img/IM4.PNG' },
            { id: 4, tutor: '/img/pic-3.jpg', thumb: '/img/IM5.PNG' },
            { id: 5, tutor: '/img/pic-5.jpg', thumb: '/img/im.PNG' },
            { id: 6, tutor: '/img/pic-6.jpg', thumb: '/img/im1.PNG' }
          ].map((course) => (
            <div key={course.id} className="box">
              <div className="tutor">
                <img src={course.tutor} alt="" />
                <div className="info">
                  <h3>john deo</h3>
                  <span>21-10-2024</span>
                </div>
              </div>
              <div className="thumb">
                <img src={course.thumb} alt="" />
              </div>
              <h3 className="title">CURSO {course.id.toString().padStart(2, '0')}</h3>
              <a href="secciones.html" className="arrow-btn">
                <i className="fas fa-arrow-right"></i>
              </a>
            </div>
          ))}
        </div>
      </section>

      <footer className="footer">
        &copy; LMS @ 2024 <span>Desarrollado por Equipo LMS</span> | Todos los derechos reservados.
      </footer>
    </div>
  );
};

export default CoursesComponent;