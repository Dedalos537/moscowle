import { WizardConfig } from '../models/wizard-step.model';

export const WIZARD_STEPS: WizardConfig[] = [
  {
    route: '/admin/dashboard',
    role: 'admin',
    steps: [
      {
        selector: 'app-header.layout__header',
        title: 'Encabezado',
        description: 'Aquí ves el título de la sección actual, notificaciones y acceso rápido a tu perfil.',
        position: 'bottom',
      },
      {
        selector: 'app-sidebar.layout__sidebar',
        title: 'Menú Lateral',
        description: 'Navega entre las secciones del panel: Usuarios, Finanzas, Sesiones, Reportes y más.',
        position: 'right',
      },
      {
        selector: '.dashboard',
        title: 'Área Principal',
        description: 'El contenido principal de cada sección se muestra aquí. Los datos se cargan automáticamente.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/users',
    role: 'admin',
    steps: [
      {
        selector: 'app-header.layout__header',
        title: 'Gestión de Usuarios',
        description: 'Desde aquí administras todos los usuarios del sistema.',
        position: 'bottom',
      },
      {
        selector: '.btn-filter',
        title: 'Filtros',
        description: 'Usa estos filtros para buscar usuarios por nombre, rol, sede o estado.',
        position: 'bottom',
      },
      {
        selector: 'app-header.layout__header',
        title: 'Crear Usuario',
        description: 'Usa el botón "Nuevo Usuario" en el encabezado para agregar terapeutas, pacientes o administradores.',
        position: 'center',
      },
      {
        selector: 'table',
        title: 'Tabla de Usuarios',
        description: 'Cada fila es un usuario. Haz clic en cualquier fila para editar sus datos.',
        position: 'top',
      },
    ],
  },
  {
    route: '/admin/finanzas',
    role: 'admin',
    steps: [
      {
        selector: 'app-header.layout__header',
        title: 'Finanzas',
        description: 'Panel de control financiero del centro.',
        position: 'bottom',
      },
      {
        selector: '.chrome-tab-bar',
        title: 'Navegación',
        description: 'Alterna entre Dashboard, Pagos, Yape y Gastos para ver diferentes vistas financieras.',
        position: 'bottom',
      },
      {
        selector: '.layout__content',
        title: 'Resumen Financiero',
        description: 'Tarjetas con totales: deuda total, ingresos reales, gastos y más indicadores clave.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/dashboard',
    role: 'terapista',
    steps: [
      {
        selector: 'app-header.layout__header',
        title: 'Panel del Terapeuta',
        description: 'Bienvenido a tu panel. Aquí ves un resumen de tu actividad.',
        position: 'bottom',
      },
      {
        selector: '.layout__content',
        title: 'Resumen de Actividad',
        description: 'Pacientes activos, sesiones de hoy, próximas citas y más indicadores.',
        position: 'center',
      },
      {
        selector: 'app-sidebar.layout__sidebar',
        title: 'Menú Lateral',
        description: 'Accede a Pacientes, Sesiones, Calendario, Mensajes y más desde aquí.',
        position: 'right',
      },
    ],
  },
  {
    route: '/therapist/sessions',
    role: 'terapista',
    steps: [
      {
        selector: 'app-header.layout__header',
        title: 'Mis Sesiones',
        description: 'Gestiona todas tus sesiones de terapia.',
        position: 'bottom',
      },
      {
        selector: '.layout__content',
        title: 'Pestañas',
        description: 'Alterna entre "Programar" una nueva sesión y ver el "Historial" de sesiones pasadas.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/dashboard',
    role: 'jugador',
    steps: [
      {
        selector: 'app-header.layout__header',
        title: 'Mi Panel',
        description: 'Bienvenido a tu espacio personal. Aquí ves tus próximas actividades.',
        position: 'bottom',
      },
      {
        selector: '.layout__content',
        title: 'Tu Resumen',
        description: 'Próximas sesiones, pagos pendientes y progreso general.',
        position: 'center',
      },
      {
        selector: 'app-sidebar.layout__sidebar',
        title: 'Menú',
        description: 'Navega a tus sesiones, pagos, progreso y mensajes.',
        position: 'right',
      },
    ],
  },
];
