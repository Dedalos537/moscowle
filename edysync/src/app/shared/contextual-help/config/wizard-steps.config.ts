import { WizardConfig } from '../models/wizard-step.model';

export const WIZARD_STEPS: WizardConfig[] = [
  // ─────────────────────────────────────────────
  // ADMIN — Dashboard
  // ─────────────────────────────────────────────
  {
    route: '/admin/dashboard',
    role: 'admin',
    steps: [
      {
        selector: '.stat-card',
        title: 'KPIs del Centro',
        description: 'Resumen rápido: terapeutas activos, pacientes, sesiones de hoy e ingresos. Cada tarjeta muestra un número clave.',
        position: 'bottom',
      },
      {
        selector: '.guidance-banner',
        title: 'Alertas Importantes',
        description: 'Banner con pacientes incompletos o acciones pendientes. Haz clic en "Ver Pendientes" para revisar.',
        position: 'bottom',
      },
      {
        selector: '.summary-card',
        title: 'Resumen General',
        description: 'Tarjetas con métricas: terapeutas, pacientes activos, sesiones totales y porcentaje de cumplimiento.',
        position: 'center',
      },
      {
        selector: '.card--span-2',
        title: 'Flujo de Caja',
        description: 'Gráfico de barras comparando ingresos reales vs. proyectados por mes. Boxes de efectivo y cobranza.',
        position: 'center',
      },
      {
        selector: '.sedes-grid',
        title: 'Sedes',
        description: 'Grid con cada sede y su cantidad de pacientes. Haz clic para ver usuarios de esa sede.',
        position: 'center',
      },
      {
        selector: '.quick-payment-card',
        title: 'Pago Rápido',
        description: 'Registra un pago rápido seleccionando paciente y monto sin salir del dashboard.',
        position: 'center',
      },
      {
        selector: '.action-card',
        title: 'Accesos Rápidos',
        description: 'Enlaces directos a: Usuarios, Juegos, Reportes y Mensajes. Cada tarjeta navega a esa sección.',
        position: 'bottom',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Usuarios
  // ─────────────────────────────────────────────
  {
    route: '/admin/users',
    role: 'admin',
    steps: [
      {
        selector: '.stat-card',
        title: 'Estadísticas de Usuarios',
        description: '9 tarjetas: Total, Activos, Inactivos, Pacientes, Terapeutas, Deudores, Retirados, Admin, Supervisores.',
        position: 'bottom',
      },
      {
        selector: 'canvas[baseChart]',
        title: 'Gráficos de Distribución',
        description: '3 gráficos: usuarios por sede (barras), activos vs inactivos (donut), distribución de roles (donut).',
        position: 'center',
      },
      {
        selector: '.btn-filter',
        title: 'Filtros Rápidos',
        description: 'Filtra la tabla por: Todos, Pacientes, Terapeutas, Deudores, Retirados, Supervisores, Admin.',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Tabla de Usuarios',
        description: 'Cada fila muestra: nombre, email, rol, sede, estado y terapeuta. Edita inline o haz clic en "..." para más opciones.',
        position: 'center',
      },
      {
        selector: 'button[openActionDrawer]',
        title: 'Menú de Acciones',
        description: 'Haz clic en "..." para: Ver perfil, Editar usuario, Resetear contraseña o Eliminar.',
        position: 'right',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Sedes
  // ─────────────────────────────────────────────
  {
    route: '/admin/sedes',
    role: 'admin',
    steps: [
      {
        selector: 'input[searchQuery]',
        title: 'Buscar Sede',
        description: 'Escribe el nombre de una sede para encontrarla rápidamente.',
        position: 'bottom',
      },
      {
        selector: 'app-sede-card',
        title: 'Tarjeta de Sede',
        description: 'Cada tarjeta muestra: nombre, dirección, pacientes, sesiones e ingresos. Haz clic para ver más detalles.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Crear Nueva Sede',
        description: 'Botón "Nueva Sede" abre un formulario lateral para agregar una sede con nombre y dirección.',
        position: 'right',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Finanzas
  // ─────────────────────────────────────────────
  {
    route: '/admin/finanzas',
    role: 'admin',
    steps: [
      {
        selector: '.chrome-tab-bar',
        title: 'Pestañas de Finanzas',
        description: '4 pestañas: Dashboard (resumen), Pagos (gestión de cobros), Yape (transacciones), Gastos (nómina).',
        position: 'bottom',
      },
      {
        selector: '.bg-surface-container-lowest.rounded-xl',
        title: 'Tarjetas KPI',
        description: 'En la pestaña Dashboard: Deuda Total, Ingresos Reales, Gastos y Balance Neto. Se actualizan según el período.',
        position: 'center',
      },
      {
        selector: 'canvas[baseChart]',
        title: 'Gráficos Financieros',
        description: 'Gráficos de: Ingresos vs Gastos (líneas), Gastos por Categoría (pastel), Eficiencia de Cobranza (barra).',
        position: 'center',
      },
      {
        selector: '.chrome-tab:nth-child(2)',
        title: 'Pestaña de Pagos',
        description: 'Gestiona cobros: tabla de pacientes con deuda, registrar pagos, configurar planes, ver historial.',
        position: 'bottom',
      },
      {
        selector: '.chrome-tab:nth-child(3)',
        title: 'Pestaña Yape',
        description: 'Importa transacciones de Yape, revisa pagos pendientes y empareja con pacientes.',
        position: 'bottom',
      },
      {
        selector: '.chrome-tab:nth-child(4)',
        title: 'Pestaña de Gastos',
        description: 'Nómina de terapeutas con horas y montos. Historial de gastos operativos y botón para registrar nuevos.',
        position: 'bottom',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Sesiones
  // ─────────────────────────────────────────────
  {
    route: '/admin/sessions',
    role: 'admin',
    steps: [
      {
        selector: 'app-calendar-widget',
        title: 'Calendario de Sesiones',
        description: 'Vista mensual con eventos de sesiones. Haz clic en un día para ver las sesiones programadas.',
        position: 'center',
      },
      {
        selector: 'app-select[selectedTherapistId]',
        title: 'Filtrar por Terapeuta',
        description: 'Selecciona un terapeuta para ver solo sus sesiones en el calendario.',
        position: 'bottom',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Crear Sesión',
        description: 'Botón "Nueva Programación" abre un modal para crear sesiones: selecciona terapeuta, paciente, fecha y hora.',
        position: 'right',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Gastos
  // ─────────────────────────────────────────────
  {
    route: '/admin/expenses',
    role: 'admin',
    steps: [
      {
        selector: 'table',
        title: 'Nómina de Terapeutas',
        description: 'Tabla con: terapeuta, contrato, horas trabajadas, monto a pagar, pagado y pendiente. Haz clic en "Pagar" para registrar.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="secondary"]',
        title: 'Registrar Gasto',
        description: 'Botón "Registrar Gasto Operativo" abre un modal para agregar gastos: categoría, monto, método y comprobante.',
        position: 'right',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Reportes
  // ─────────────────────────────────────────────
  {
    route: '/admin/reports',
    role: 'admin',
    steps: [
      {
        selector: '.stat-card',
        title: 'KPIs del Período',
        description: 'Tarjetas de: Pacientes Activos, Terapeutas, Sesiones Totales y Precisión Global del sistema.',
        position: 'bottom',
      },
      {
        selector: 'canvas[baseChart]',
        title: 'Gráfico de Tendencia',
        description: 'Comparativa visual: barras de Proyectado vs Recaudado vs Deuda. Línea de evolución financiera.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Exportar y Analizar',
        description: 'Botones: "Análisis Llama AI" (genera análisis IA), "Reporte Semanal" (envía), "Exportar CSV" (descarga datos).',
        position: 'right',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Mensajes
  // ─────────────────────────────────────────────
  {
    route: '/admin/messages',
    role: 'admin',
    steps: [
      {
        selector: 'table',
        title: 'Bandeja de Mensajes',
        description: 'Lista de mensajes con: fecha, remitente, urgencia, análisis de IA y acciones. Los no leídos tienen badge rojo.',
        position: 'center',
      },
      {
        selector: 'button[viewAnalysis]',
        title: 'Análisis IA',
        description: 'Haz clic para ver el análisis completo: sentimiento, intención, confianza y respuesta sugerida por IA.',
        position: 'right',
      },
      {
        selector: 'a[href="mailto:"]',
        title: 'Responder',
        description: 'Haz clic en "Responder" para abrir tu cliente de email y contestar al mensaje.',
        position: 'center',
      },
      {
        selector: 'a[href="wa.me/"]',
        title: 'WhatsApp',
        description: 'Haz clic en "WhatsApp" para enviar una respuesta directa por WhatsApp al remitente.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Juegos
  // ─────────────────────────────────────────────
  {
    route: '/admin/games',
    role: 'admin',
    steps: [
      {
        selector: 'app-button[variant="primary"]',
        title: 'Subir Juego',
        description: 'Botón "Subir Juego" abre un modal para agregar un juego HTML al catálogo.',
        position: 'right',
      },
      {
        selector: '.aspect-video',
        title: 'Vista Previa',
        description: 'Cada juego muestra una vista previa. Haz clic en "Abrir" para verlo en pantalla completa.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="danger"]',
        title: 'Eliminar Juego',
        description: 'Haz clic en "Eliminar" para quitar un juego del catálogo. Se pedirá confirmación.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Perfil
  // ─────────────────────────────────────────────
  {
    route: '/admin/profile',
    role: 'admin',
    steps: [
      {
        selector: 'app-input#profile-username',
        title: 'Nombre de Usuario',
        description: 'Edita tu nombre de usuario. Los cambios se guardan con el botón "Guardar Cambios".',
        position: 'bottom',
      },
      {
        selector: 'app-input#profile-password',
        title: 'Cambiar Contraseña',
        description: 'Ingresa tu nueva contraseña y confírmala. Se recomienda usar una contraseña fuerte.',
        position: 'bottom',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Guardar',
        description: 'Haz clic en "Guardar Cambios" para actualizar tu perfil o contraseña.',
        position: 'right',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Logs
  // ─────────────────────────────────────────────
  {
    route: '/admin/logs',
    role: 'admin',
    steps: [
      {
        selector: '.logs__level-btn',
        title: 'Filtrar por Nivel',
        description: 'Filtra logs por nivel: INFO, WARNING, ERROR. Los botones se iluminan cuando están activos.',
        position: 'bottom',
      },
      {
        selector: '.logs__search',
        title: 'Buscar en Logs',
        description: 'Escribe una palabra clave para buscar en todos los mensajes de log.',
        position: 'bottom',
      },
      {
        selector: '.logs__auto-btn',
        title: 'Auto-actualizar',
        description: 'Activa para que los logs se actualicen cada 5 segundos automáticamente.',
        position: 'right',
      },
      {
        selector: '.log-entry',
        title: 'Entrada de Log',
        description: 'Cada entrada muestra: nivel (color), timestamp y mensaje. Haz clic para expandir y ver el detalle completo.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — API Tokens
  // ─────────────────────────────────────────────
  {
    route: '/admin/api-tokens',
    role: 'admin',
    steps: [
      {
        selector: 'app-button[variant="primary"]',
        title: 'Generar Token',
        description: 'Botón "Generar Token" crea un nuevo token de API. Solo se muestra una vez, cópialo inmediatamente.',
        position: 'right',
      },
      {
        selector: 'table',
        title: 'Tokens Existentes',
        description: 'Tabla con: ID del token, fecha de creación y estado (Activo/Inactivo). Revoca los que ya no uses.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="danger"]',
        title: 'Desactivar Token',
        description: 'Haz clic en "Desactivar" para revocar un token. No se puede recuperar después.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // ADMIN — Yape Import
  // ─────────────────────────────────────────────
  {
    route: '/admin/yape-import',
    role: 'admin',
    steps: [
      {
        selector: '.bg-gradient-to-br',
        title: 'Resumen de Importaciones',
        description: '3 tarjetas: Total Transacciones, Pendientes de Revisión y Buscador.',
        position: 'bottom',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Importar Archivo',
        description: 'Botón "Importar Archivo" abre un modal para subir CSV o Excel de Yape.',
        position: 'right',
      },
      {
        selector: 'table',
        title: 'Transacciones',
        description: 'Tabla con: fecha, remitente, monto, mensaje y categoría. Las pendientes tienen fondo amarillo.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // TERAPEUTA — Dashboard
  // ─────────────────────────────────────────────
  {
    route: '/therapist/dashboard',
    role: 'terapista',
    steps: [
      {
        selector: 'app-header',
        title: 'Tu Panel Diario',
        description: 'Resumen: próxima sesión con título y hora, porcentaje de cumplimiento y sesiones completadas hoy.',
        position: 'bottom',
      },
      {
        selector: 'main',
        title: 'Contenido Principal',
        description: 'Dashboard con sesiones de hoy, progreso de pacientes y estadísticas. Todo se actualiza en tiempo real.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // TERAPEUTA — Sesiones
  // ─────────────────────────────────────────────
  {
    route: '/therapist/sessions',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Gestión de Sesiones',
        description: 'Pestañas: "Programar" para agendar (paciente, fecha, hora, modalidad) e "Historial" para sesiones pasadas.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // TERAPEUTA — Pacientes
  // ─────────────────────────────────────────────
  {
    route: '/therapist/patients',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Mis Pacientes',
        description: 'Lista de tus pacientes asignados. Haz clic en "Ver detalle" para ver historial, progreso y programar sesiones.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // TERAPEUTA — Calendario
  // ─────────────────────────────────────────────
  {
    route: '/therapist/calendar',
    role: 'terapista',
    steps: [
      {
        selector: 'main',
        title: 'Calendario Semanal',
        description: 'Vista de tus sesiones por semana. Navega con las flechas. Haz clic en una sesión para ver detalles.',
        position: 'center',
      },
    ],
  },

  // ─────────────────────────────────────────────
  // TERAPEUTA — Juegos
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // TERAPEUTA — Reportes
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // TERAPEUTA — Analíticas IA
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // TERAPEUTA — Mensajes
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // TERAPEUTA — Perfil
  // ─────────────────────────────────────────────
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
  // PACIENTE — Dashboard
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

  // ─────────────────────────────────────────────
  // PACIENTE — Sesiones
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // PACIENTE — Pagos
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // PACIENTE — Progreso
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // PACIENTE — Calendario
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // PACIENTE — Mensajes
  // ─────────────────────────────────────────────
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

  // ─────────────────────────────────────────────
  // PACIENTE — Mi Terapeuta
  // ─────────────────────────────────────────────
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
