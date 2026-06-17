import { WizardConfig } from '../models/wizard-step.model';

export const WIZARD_STEPS: WizardConfig[] = [
  // ─────────────────────────────────────────────
  // ADMIN (13 pages)
  // ─────────────────────────────────────────────
  {
    route: '/admin/dashboard',
    role: 'admin',
    steps: [
      {
        selector: 'app-sidebar.layout__sidebar',
        title: 'Menú Lateral',
        description: 'Navega entre: Usuarios, Sedes, Finanzas, Sesiones, Reportes y más. El menú se adapta a tu rol.',
        position: 'right',
      },
      {
        selector: 'main.layout__content',
        title: 'Resumen General',
        description: 'KPIs en tiempo real: terapeutas, pacientes activos, sesiones del día e ingresos. Cada tarjeta es clicable.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/users',
    role: 'admin',
    steps: [
      {
        selector: '.btn-filter',
        title: 'Filtros por Rol',
        description: 'Filtra: Todos, Pacientes, Terapeutas, Deudores, Retirados, Supervisores, Admin.',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Tabla de Usuarios',
        description: 'Cada fila es un usuario. Haz clic en "Ver" para editar datos, cambiar rol o activar/desactivar.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/sedes',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Gestión de Sedes',
        description: 'Cada tarjeta muestra una sede con estadísticas: pacientes, sesiones e ingresos. Haz clic para editar.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/finanzas',
    role: 'admin',
    steps: [
      {
        selector: '.chrome-tab-bar',
        title: 'Pestañas de Navegación',
        description: 'Alterna entre: Resumen (KPIs), Pagos (cobros), Yape (importar), Gastos (nómina).',
        position: 'bottom',
      },
      {
        selector: 'main.layout__content',
        title: 'Resumen Financiero',
        description: 'Tarjetas con: deuda pendiente, ingresos del mes, gastos y balance neto. Se actualiza al cambiar de pestaña.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/sessions',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Sesiones Globales',
        description: 'Selecciona fechas en el calendario, elige paciente y terapeuta, guarda la sesión masiva.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/expenses',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Nómina y Gastos',
        description: 'Registra pagos a terapeutas, gastos fijos y variables. Usa "Registrar" para agregar nuevos.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/reports',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Reportes del Centro',
        description: 'Selecciona período y sede. Genera PDFs con métricas financieras, asistencia y rendimiento.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/messages',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Mensajería',
        description: 'Selecciona un contacto para chatear en tiempo real. Los mensajes se reciben automáticamente.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/games',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Juegos Terapéuticos',
        description: 'Activa o desactiva juegos según las necesidades del centro. Configura parámetros.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/profile',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Tu Perfil',
        description: 'Actualiza nombre, email y teléfono. Cambia tu contraseña desde aquí.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/logs',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Visor de Logs',
        description: 'Revisa eventos del sistema: logins, creaciones, ediciones y errores. Filtra por fecha y tipo.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/api-tokens',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Tokens de API',
        description: 'Gestiona tokens para integraciones externas. Revoca los que ya no uses.',
        position: 'center',
      },
    ],
  },
  {
    route: '/admin/yape-import',
    role: 'admin',
    steps: [
      {
        selector: 'main.layout__content',
        title: 'Importar Yape',
        description: 'Sube un CSV o ingresa datos manualmente para importar transacciones de Yape.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // TERAPEUTA (9 pages)
  // ─────────────────────────────────────────────
  {
    route: '/therapist/dashboard',
    role: 'terapista',
    steps: [
      {
        selector: 'app-header',
        title: 'Tu Panel',
        description: 'Resumen diario: próxima sesión con título y hora, porcentaje de cumplimiento y sesiones completadas.',
        position: 'bottom',
      },
      {
        selector: 'main',
        title: 'Contenido Principal',
        description: 'Dashboard con sesiones de hoy, progreso de pacientes y estadísticas en tiempo real.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/sessions',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Mis Sesiones',
        description: 'Pestañas: "Programar" para agendar (paciente, fecha, hora, modalidad) e "Historial" para pasadas.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/patients',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Mis Pacientes',
        description: 'Lista de pacientes asignados. "Ver detalle" muestra historial, progreso y permite programar sesiones.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/calendar',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Calendario',
        description: 'Vista semanal de sesiones. Navega con las flechas. Haz clic en una sesión para ver detalles.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/games',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Juegos Terapéuticos',
        description: 'Selecciona un juego para usar con tu paciente. Son interactivos y educativos.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/reports',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Reportes',
        description: 'Genera reportes por período: sesiones, pacientes atendidos y progreso.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/analytics',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Analíticas IA',
        description: 'Métricas inteligentes: tasa de asistencia, precisión de sesiones, adaptaciones y tendencia de progreso.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/messages',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Mensajes',
        description: 'Selecciona un paciente o administrador de la lista para chatear en tiempo real.',
        position: 'center',
      },
    ],
  },
  {
    route: '/therapist/profile',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Tu Perfil',
        description: 'Actualiza nombre, teléfono, especialidad. Cambia tu contraseña desde aquí.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // PACIENTE (7 pages)
  // ─────────────────────────────────────────────
  {
    route: '/patient/dashboard',
    role: 'jugador',
    steps: [
      {
        selector: 'app-header',
        title: 'Tu Panel',
        description: 'Resumen personal: próxima sesión, pagos pendientes y nivel de progreso general.',
        position: 'bottom',
      },
      {
        selector: 'main',
        title: 'Tu Resumen',
        description: 'Próximas sesiones, pagos pendientes y progreso. Todo se actualiza automáticamente.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/sessions',
    role: 'jugador',
    steps: [
      {
        selector: 'main',
        title: 'Mis Sesiones',
        description: 'Próximas sesiones con fecha, hora y terapeuta. Historial de sesiones completadas.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/payments',
    role: 'jugador',
    steps: [
      {
        selector: 'main',
        title: 'Mis Pagos',
        description: 'Tu plan de pago con cuotas y fechas. Historial de pagos realizados y estado de cuenta.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/progress',
    role: 'jugador',
    steps: [
      {
        selector: 'main',
        title: 'Mi Progreso',
        description: 'Gráficos de asistencia, sesiones completadas y evolución a lo largo del tiempo.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/calendar',
    role: 'jugador',
    steps: [
      {
        selector: 'main',
        title: 'Mi Calendario',
        description: 'Vista de sesiones programadas. Las fechas con sesión están marcadas. Navega entre semanas.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/messages',
    role: 'jugador',
    steps: [
      {
        selector: 'main',
        title: 'Mensajes',
        description: 'Conversa con tu terapeuta en tiempo real. Los mensajes son privados y seguros.',
        position: 'center',
      },
    ],
  },
  {
    route: '/patient/my-therapist',
    role: 'jugador',
    steps: [
      {
        selector: 'main',
        title: 'Mi Terapeuta',
        description: 'Información de contacto, especialidad y horario. Usa el botón para enviarle un mensaje.',
        position: 'center',
      },
    ],
  },
];
