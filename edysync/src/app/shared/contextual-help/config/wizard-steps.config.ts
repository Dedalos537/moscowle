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
        selector: 'h1.text-2xl',
        title: 'Panel Diario del Terapeuta',
        description: 'Tu nombre y mensaje personalizado. Resumen rápido de lo que necesitas hacer hoy.',
        position: 'bottom',
      },
      {
        selector: '.grid.grid-cols-2',
        title: 'Sesión de Hoy y Estadísticas',
        description: 'Izquierda: sesión actual (si hay). Derecha: sesiones completadas, faltadas y total del mes.',
        position: 'bottom',
      },
      {
        selector: '.lg-col-span-2',
        title: 'Acciones Rápidas',
        description: 'Botón "Siguiente Sesión" para ver detalles y "Programar Nueva Sesión" para agendar.',
        position: 'right',
      },
      {
        selector: 'app-messages-widget',
        title: 'Mensajes Recientes',
        description: 'Últimos mensajes de pacientes. Haz clic en "Ver todo" para ir a la bandeja completa.',
        position: 'top',
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
        selector: 'a[routerLink="/therapist/sessions/schedule"]',
        title: 'Agendar Nueva Sesión',
        description: 'Botón "Agendar Nueva Sesión" abre el formulario para programar: paciente, fecha, hora y duración.',
        position: 'right',
      },
      {
        selector: '.space-y-4',
        title: 'Pestañas de Sesiones',
        description: 'Cambia entre "Próximas" (sesiones futuras) e "Historial" (sesiones completadas).',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Tabla de Sesiones',
        description: 'Cada fila muestra: paciente, fecha, hora, modalidad y estado. Haz clic en una para ver detalles.',
        position: 'center',
      },
      {
        selector: 'app-select',
        title: 'Filtrar por Estado',
        description: 'Filtra sesiones por: Todas, Completadas, Programadas o Canceladas.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Mis Pacientes',
        description: 'Lista de todos tus pacientes asignados con su información básica.',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Tabla de Pacientes',
        description: 'Cada fila: nombre, edad, padecimiento, sesiones totales y última sesión. Haz clic en "Ver" para ver el detalle completo.',
        position: 'center',
      },
      {
        selector: '.relative.pl-6',
        title: 'Estado del Paciente',
        description: 'Indicador visual del estado: Activo (verde), En Evaluación (amarillo) o Inactivo (gris).',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Calendario Terapéutico',
        description: 'Vista mensual de tus sesiones programadas. Los días con sesión están resaltados.',
        position: 'bottom',
      },
      {
        selector: '.calendar-widget',
        title: 'Calendario Interactivo',
        description: 'Haz clic en un día para ver las sesiones programadas. Las sesiones aparecen con el nombre del paciente.',
        position: 'center',
      },
      {
        selector: 'button[arrowBtn]',
        title: 'Navegar Meses',
        description: 'Flechas izquierda/derecha para moverte entre meses.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Juegos Terapéuticos',
        description: 'Catálogo de juegos interactivos para usar durante las sesiones con pacientes.',
        position: 'bottom',
      },
      {
        selector: '.grid.grid-cols-3',
        title: 'Selecciona un Juego',
        description: 'Cada juego muestra imagen, nombre y descripción. Haz clic en "Abrir" para iniciar con tu paciente.',
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
        selector: 'h1.text-2xl',
        title: 'Reportes y Análisis',
        description: 'Genera reportes detallados de tus sesiones, pacientes y progreso.',
        position: 'bottom',
      },
      {
        selector: '.grid.grid-cols-2.gap-4',
        title: 'KPIs del Período',
        description: 'Tarjetas con métricas: sesiones completadas, asistencia promedio, pacientes activos y evaluaciones.',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Tabla de Reportes',
        description: 'Detalle de sesiones: paciente, fecha, modalidad, duración y estado de asistencia.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Exportar Datos',
        description: 'Haz clic en "Exportar CSV" para descargar los datos o "Análisis IA" para generar un análisis inteligente.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Analíticas con IA',
        description: 'Métricas inteligentes generadas por inteligencia artificial sobre tu desempeño y pacientes.',
        position: 'bottom',
      },
      {
        selector: '.grid.grid-cols-2.gap-4',
        title: 'Métricas Clave',
        description: 'Tarjetas: tasa de asistencia, precisión de sesiones, adaptaciones recomendadas y tendencia de progreso.',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Análisis Detallado',
        description: 'Tabla con análisis por paciente: tendencia, recomendaciones y evaluación de progreso.',
        position: 'center',
      },
      {
        selector: '.ai-badge',
        title: 'Generado por IA',
        description: 'Indicador de contenido generado por inteligencia artificial. Los datos son una estimación.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Mensajería',
        description: 'Comunícate con tus pacientes y el equipo administrativo en tiempo real.',
        position: 'bottom',
      },
      {
        selector: '.w-\\[300px\\]',
        title: 'Lista de Conversaciones',
        description: 'Selecciona un paciente o administrador de la lista para ver el historial de mensajes.',
        position: 'right',
      },
      {
        selector: 'app-chat',
        title: 'Zona de Chat',
        description: 'Escribe tu mensaje y presiona Enter para enviar. Los archivos se envían con el botón de adjuntar.',
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
        selector: 'h1.text-2xl',
        title: 'Tu Perfil Profesional',
        description: 'Actualiza tu información personal y profesional visible para los pacientes.',
        position: 'bottom',
      },
      {
        selector: 'form',
        title: 'Campos del Perfil',
        description: 'Edita: nombre completo, teléfono, especialidad, experiencia y biografía profesional.',
        position: 'center',
      },
      {
        selector: 'app-button[variant="primary"]',
        title: 'Guardar Cambios',
        description: 'Haz clic en "Guardar" para actualizar tu perfil. Los cambios son visibles inmediatamente.',
        position: 'right',
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
        selector: 'h1.text-2xl.font-bold',
        title: 'Bienvenido, Paciente',
        description: 'Tu nombre y resumen personal. Aquí ves un vistazo rápido de tu estado.',
        position: 'bottom',
      },
      {
        selector: '.bg-on-primary-container',
        title: 'Estado de la Sesión',
        description: 'Indica si tienes sesión programada hoy o si no hay nada pendiente.',
        position: 'bottom',
      },
      {
        selector: '.bg-surface-container-lowest.rounded-3xl',
        title: 'Resumen del Día',
        description: 'Sesión actual, pagos pendientes y nivel de progreso. Todo en un vistazo.',
        position: 'right',
      },
      {
        selector: '.grid.gap-4',
        title: 'Acciones Rápidas',
        description: 'Botones para: Ver mis pagos, mi progreso y mis sesiones programadas.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Mis Sesiones',
        description: 'Gestiona y revisa todas tus sesiones terapéuticas.',
        position: 'bottom',
      },
      {
        selector: '.grid.grid-cols-2.gap-4',
        title: 'Próximas Sesiones',
        description: 'Tus sesiones programadas con: fecha, hora, terapeuta y modalidad (Presencial/Online).',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Historial de Sesiones',
        description: 'Sesiones completadas con resultado y duración. Puedes exportar el historial.',
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
        selector: 'h1.text-2xl',
        title: 'Mis Pagos',
        description: 'Consulta tu plan de pago y historial de transacciones.',
        position: 'bottom',
      },
      {
        selector: '.space-y-6',
        title: 'Resumen de Pagos',
        description: 'Monto total, pagado y pendiente. Gráfico de progreso de tu plan.',
        position: 'bottom',
      },
      {
        selector: 'table',
        title: 'Historial de Transacciones',
        description: 'Cada pago registrado con: fecha, monto, método de pago y estado (Pagado/Pendiente).',
        position: 'center',
      },
      {
        selector: '.card',
        title: 'Estado de Cuenta',
        description: 'Detalle de cuotas: número, fecha de vencimiento y monto. Marca como pagadas.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Mi Progreso',
        description: 'Evolución de tu tratamiento con gráficos y estadísticas.',
        position: 'bottom',
      },
      {
        selector: '.stats-grid',
        title: 'Estadísticas Clave',
        description: 'Tarjetas: sesiones completadas, porcentaje de asistencia, nivel actual y logros.',
        position: 'bottom',
      },
      {
        selector: 'canvas[baseChart]',
        title: 'Gráfico de Evolución',
        description: 'Línea de tiempo: sesiones por mes, tendencia de progreso y comparativa con el mes anterior.',
        position: 'center',
      },
      {
        selector: '.grid.grid-cols-2.gap-4',
        title: 'Análisis Detallado',
        description: 'Gráficos de distribución por tipo de sesión, modalidad y resultados obtenidos.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Mi Calendario',
        description: 'Vista de tus sesiones programadas por mes.',
        position: 'bottom',
      },
      {
        selector: '.calendar-widget',
        title: 'Calendario Interactivo',
        description: 'Los días con sesión están marcados. Haz clic en un día para ver detalles de la sesión.',
        position: 'center',
      },
      {
        selector: 'button[arrowBtn]',
        title: 'Navegar Meses',
        description: 'Flechas izquierda/derecha para moverte entre meses.',
        position: 'right',
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
        selector: 'h1.text-2xl',
        title: 'Mensajes',
        description: 'Comunícate directamente con tu terapeuta en tiempo real.',
        position: 'bottom',
      },
      {
        selector: '.w-\\[300px\\]',
        title: 'Lista de Conversaciones',
        description: 'Selecciona a tu terapeuta de la lista para ver el historial de mensajes.',
        position: 'right',
      },
      {
        selector: 'app-chat',
        title: 'Zona de Chat',
        description: 'Escribe tu mensaje y presiona Enter. Puedes adjuntar archivos con el botón de clip.',
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
        selector: 'h1.text-2xl',
        title: 'Mi Terapeuta',
        description: 'Información completa de tu terapeuta asignado.',
        position: 'bottom',
      },
      {
        selector: '.rounded-3xl',
        title: 'Perfil del Terapeuta',
        description: 'Foto, nombre, especialidad, experiencia y horarios de atención.',
        position: 'center',
      },
      {
        selector: 'app-button',
        title: 'Enviar Mensaje',
        description: 'Haz clic para iniciar una conversación directa con tu terapeuta.',
        position: 'right',
      },
    ],
  },
];
