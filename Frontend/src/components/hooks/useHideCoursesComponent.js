import { useEffect } from 'react';

const useHideCoursesComponent = () => {
  useEffect(() => {
    // Función para ocultar elementos del CoursesComponent
    const hideCoursesElements = () => {
      // Ocultar elementos específicos del curso que puedan persistir
      const coursesElements = [
        '.courses-component',
        '.header', // header del curso
        '.side-bar', // sidebar del curso
        '.profile.active', // profile dropdown del curso
        '.search-form.active', // search form del curso
        '.notification-bar.active', // notification bar del curso
        '.courses', // sección de cursos
        '.footer' // footer del curso si existe
      ];

      coursesElements.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(element => {
          // Solo ocultar si pertenece al courses component
          if (element.closest('.courses-component')) {
            element.style.display = 'none !important';
            element.style.visibility = 'hidden !important';
            element.style.opacity = '0 !important';
            element.style.zIndex = '-9999 !important';
            element.style.position = 'absolute !important';
            element.style.left = '-9999px !important';
            element.style.top = '-9999px !important';
          }
        });
      });

      // Remover clases activas del courses component
      const activeElements = document.querySelectorAll('.courses-component .active');
      activeElements.forEach(element => {
        element.classList.remove('active');
      });

      // Limpiar estilos en el body que puedan afectar
      document.body.classList.remove('courses-active');
      document.body.style.overflow = 'auto';
    };

    // Ejecutar inmediatamente
    hideCoursesElements();

    // Ejecutar en el siguiente tick para asegurar que se aplique
    const timeoutId = setTimeout(hideCoursesElements, 0);

    // Limpiar al desmontar
    return () => {
      clearTimeout(timeoutId);
    };
  }, []);

  // También limpiar cuando el componente se monta
  useEffect(() => {
    const cleanupCoursesDOM = () => {
      // Remover cualquier elemento del courses component que pueda existir
      const coursesContainer = document.querySelector('.courses-component');
      if (coursesContainer && !window.location.pathname.includes('courses')) {
        coursesContainer.remove();
      }
    };

    cleanupCoursesDOM();
  }, []);
};

// Ejemplo de uso en cualquier componente:
export default useHideCoursesComponent;