import { RoleHelp } from '../models/help-content.model';

export const HELP_CONTENT: RoleHelp[] = [
  // ─── ADMIN ──────────────────────────────────────────────────────────
  {
    role: 'admin',
    pages: [
      {
        route: '/admin/dashboard',
        content: {
          title: 'Panel de Administración',
          description: 'Vista general del sistema con indicadores clave.',
          icon: ['fas', 'chart-pie'],
          sections: [
            {
              title: 'Resumen',
              content: 'Este panel muestra estadísticas en tiempo real: total de terapeutas, pacientes activos, sesiones del día, ingresos del mes y deudores.',
              icon: ['fas', 'gauge-high'],
              items: [
                'Las tarjetas se actualizan automáticamente al cargar la página.',
                'Haz clic en cualquier tarjeta para ir al detalle.',
                'Los gráficos muestran tendencias semanales/mensuales.',
              ],
            },
          ],
          tips: [
            'Usa el menú lateral para navegar entre secciones.',
            'Los datos se actualizan cada vez que recargas la página.',
          ],
        },
      },
      {
        route: '/admin/sedes',
        content: {
          title: 'Gestión de Sedes',
          description: 'Administra las sedes o sucursales del centro.',
          icon: ['fas', 'building'],
          sections: [
            {
              title: 'Administrar Sedes',
              content: 'Desde aquí puedes crear, editar y desactivar sedes. Cada sede agrupa terapeutas y pacientes.',
              items: [
                'Crea una nueva sede con nombre y dirección.',
                'Edita datos de sedes existentes.',
                'Desactiva una sede sin eliminar sus datos.',
              ],
            },
          ],
        },
      },
      {
        route: '/admin/users',
        content: {
          title: 'Usuarios',
          description: 'Gestión completa de terapeutas, pacientes y personal.',
          icon: ['fas', 'users-cog'],
          sections: [
            {
              title: 'Listado de Usuarios',
              content: 'Tabla con todos los usuarios del sistema. Puedes filtrar por rol, sede y estado.',
              items: [
                'Usa los filtros superiores para encontrar usuarios rápidamente.',
                'Haz clic en un usuario para ver su detalle y editarlo.',
                'El botón "Nuevo Usuario" abre el formulario de creación.',
              ],
            },
          ],
          tips: ['Los usuarios inactivos no pueden iniciar sesión.'],
          relatedLinks: [
            { label: 'Crear nuevo usuario', route: '/admin/users', icon: ['fas', 'user-plus'] },
          ],
        },
      },
      {
        route: '/admin/finanzas',
        content: {
          title: 'Finanzas',
          description: 'Control financiero del centro: ingresos, deudas y cobranzas.',
          icon: ['fas', 'wallet'],
          sections: [
            {
              title: 'Panel Financiero',
              content: 'Resume la situación financiera general. Incluye total adeudado, pacientes al día, y morosos.',
              items: [
                'Los montos se calculan automáticamente según los planes de pago.',
                'Identifica pacientes con deuda en la tabla inferior.',
                'Usa los botones de acción para gestionar cobranzas.',
              ],
            },
          ],
          tips: ['Revisa la pestaña "Deudores" para ver pacientes con pagos vencidos.'],
        },
      },
      {
        route: '/admin/payments',
        content: {
          title: 'Pagos',
          description: 'Registro de pagos recibidos y pendientes.',
          icon: ['fas', 'money-bill-wave'],
          sections: [
            {
              title: 'Gestión de Pagos',
              content: 'Aquí puedes registrar pagos de pacientes, ver historial y gestionar deudas.',
              items: [
                'Registra pagos individuales o masivos.',
                'El historial muestra todos los pagos registrados.',
                'Los recibos se generan automáticamente.',
              ],
            },
          ],
        },
        tabs: [
            {
              tab: 'historial',
              content: {
                title: 'Historial de Pagos',
                description: 'Registro cronológico de todos los pagos.',
                icon: ['fas', 'clock'],
                sections: [
                  {
                    title: 'Navegación',
                    content: 'Busca pagos por fecha, paciente o monto. Cada fila muestra detalles del pago.',
                  },
                ],
              },
            },
            {
              tab: 'yape',
              content: {
                title: 'Importar Yape',
                description: 'Importa pagos desde la app Yape.',
                icon: ['fas', 'mobile-alt'],
                sections: [
                  {
                    title: 'Proceso',
                    content: 'Sube el archivo de extracto Yape (CSV) para importar pagos automáticamente.',
                    items: [
                      'Descarga el extracto desde Yape.',
                      'Súbelo aquí y el sistema emparejará los pagos con pacientes.',
                    ],
                  },
                ],
              },
            },
          ],
      },
      {
        route: '/admin/sessions',
        content: {
          title: 'Sesiones',
          description: 'Gestión de sesiones de terapia programadas y realizadas.',
          icon: ['fas', 'calendar-check'],
          sections: [
            {
              title: 'Sesiones',
              content: 'Visualiza todas las sesiones del centro. Filtra por terapeuta, paciente, fecha o estado.',
              items: [
                'Las sesiones aparecen con estado: programada, en curso, completada o cancelada.',
                'Puedes cancelar sesiones desde aquí.',
                'Usa el calendario para ver la distribución semanal.',
              ],
            },
          ],
        },
      },
      {
        route: '/admin/expenses',
        content: {
          title: 'Gastos',
          description: 'Registro de gastos operativos del centro.',
          icon: ['fas', 'receipt'],
          sections: [
            {
              title: 'Gestionar Gastos',
              content: 'Registra y categoriza los gastos del centro: alquiler, insumos, servicios, etc.',
              items: [
                'Cada gasto debe tener categoría, monto y comprobante.',
                'Los gastos se reflejan en los reportes financieros.',
              ],
            },
          ],
        },
      },
      {
        route: '/admin/messages',
        content: {
          title: 'Mensajes',
          description: 'Bandeja de mensajes del sistema.',
          icon: ['fas', 'envelope'],
          sections: [
            {
              title: 'Chat',
              content: 'Comunícate con terapeutas y pacientes. Los mensajes son en tiempo real.',
              items: [
                'Selecciona un contacto de la lista lateral.',
                'Los mensajes nuevos aparecen automáticamente.',
                'Puedes enviar archivos adjuntos.',
              ],
            },
          ],
        },
      },
      {
        route: '/admin/reports',
        content: {
          title: 'Reportes',
          description: 'Genera reportes del centro en PDF.',
          icon: ['fas', 'file-alt'],
          sections: [
            {
              title: 'Reportes',
              content: 'Genera reportes personalizados: asistencias, finanzas, sesiones, etc.',
              items: [
                'Selecciona el tipo de reporte y el rango de fechas.',
                'Los reportes se descargan en PDF.',
                'Puedes programar reportes recurrentes.',
              ],
            },
          ],
        },
      },
      {
        route: '/admin/games',
        content: {
          title: 'Juegos',
          description: 'Configura los juegos terapéuticos disponibles.',
          icon: ['fas', 'gamepad'],
          sections: [
            {
              title: 'Juegos',
              content: 'Administra el catálogo de juegos: activa/desactiva y configura parámetros.',
            },
          ],
        },
      },
      {
        route: '/admin/profile',
        content: {
          title: 'Mi Perfil',
          description: 'Tu información personal y configuración de cuenta.',
          icon: ['fas', 'user-circle'],
          sections: [
            {
              title: 'Perfil',
              content: 'Actualiza tus datos personales, cambia tu contraseña y configura preferencias.',
            },
          ],
        },
      },
      {
        route: '/admin/api-tokens',
        content: {
          title: 'API Tokens',
          description: 'Gestiona tokens de acceso para integraciones.',
          icon: ['fas', 'key'],
          sections: [
            {
              title: 'Tokens',
              content: 'Crea y revoca tokens de API para integraciones externas.',
              items: [
                'Cada token tiene permisos específicos.',
                'Revoca tokens que ya no uses.',
              ],
            },
          ],
        },
      },
      {
        route: '/admin/ai',
        content: {
          title: 'Entrenamiento IA',
          description: 'Configura el asistente IA del sistema.',
          icon: ['fas', 'robot'],
          sections: [
            {
              title: 'IA',
              content: 'Entrena y configura el asistente virtual para que responda según las necesidades del centro.',
            },
          ],
        },
      },
      {
        route: '/admin/logs',
        content: {
          title: 'Logs del Sistema',
          description: 'Registro de actividad del sistema.',
          icon: ['fas', 'list'],
          sections: [
            {
              title: 'Logs',
              content: 'Visualiza el registro de eventos del sistema para auditoría y depuración.',
            },
          ],
        },
      },
    ],
  },

  // ─── THERAPIST ──────────────────────────────────────────────────────
  {
    role: 'terapista',
    pages: [
      {
        route: '/therapist/dashboard',
        content: {
          title: 'Panel del Terapeuta',
          description: 'Tu vista general con pacientes, sesiones y actividades.',
          icon: ['fas', 'chart-pie'],
          sections: [
            {
              title: 'Resumen',
              content: 'Este panel muestra tus pacientes activos, sesiones del día, próximas citas y notificaciones.',
              items: [
                'Las tarjetas se actualizan al cargar la página.',
                'Los próximos eventos aparecen ordenados por fecha.',
              ],
            },
          ],
          tips: [
            'Revisa tu calendario para ver la semana completa.',
            'Usa el menú lateral para ir a pacientes o sesiones.',
          ],
        },
      },
      {
        route: '/therapist/sessions',
        content: {
          title: 'Mis Sesiones',
          description: 'Programa y gestiona tus sesiones de terapia.',
          icon: ['fas', 'calendar-alt'],
          sections: [
            {
              title: 'Sesiones',
              content: 'Aquí ves todas tus sesiones programadas y pasadas. Puedes filtrar por fecha y estado.',
              items: [
                'Las sesiones futuras se pueden cancelar o reprogramar.',
                'Al iniciar una sesión, la grabación comienza automáticamente.',
                'Completa la sesión para guardar las notas.',
              ],
            },
          ],
        },
        tabs: [
            {
              tab: 'programar',
              content: {
                title: 'Programar Sesión',
                description: 'Agenda una nueva sesión con un paciente.',
                icon: ['fas', 'plus-circle'],
                sections: [
                  {
                    title: 'Programar',
                    content: 'Selecciona paciente, fecha, hora y modalidad. La sesión quedará agendada.',
                  },
                ],
              },
            },
            {
              tab: 'historial',
              content: {
                title: 'Historial',
                description: 'Sesiones completadas anteriormente.',
                icon: ['fas', 'history'],
                sections: [
                  {
                    title: 'Historial',
                    content: 'Revisa sesiones pasadas, sus notas y grabaciones asociadas.',
                  },
                ],
              },
            },
          ],
      },
      {
        route: '/therapist/patients',
        content: {
          title: 'Mis Pacientes',
          description: 'Lista de pacientes asignados a tu cargo.',
          icon: ['fas', 'users'],
          sections: [
            {
              title: 'Pacientes',
              content: 'Visualiza todos tus pacientes. Cada tarjeta muestra información básica y progreso.',
              items: [
                'Haz clic en un paciente para ver su detalle completo.',
                'Desde el detalle puedes programar sesiones y ver su historial.',
              ],
            },
          ],
        },
      },
      {
        route: '/therapist/messages',
        content: {
          title: 'Mensajes',
          description: 'Comunicación con pacientes y administración.',
          icon: ['fas', 'envelope'],
          sections: [
            {
              title: 'Chat',
              content: 'Conversa en tiempo real con tus pacientes y con administradores.',
              items: [
                'Selecciona un contacto de la lista.',
                'Puedes enviar mensajes de texto y archivos.',
              ],
            },
          ],
        },
      },
      {
        route: '/therapist/reports',
        content: {
          title: 'Reportes',
          description: 'Genera reportes de tu actividad terapéutica.',
          icon: ['fas', 'file-alt'],
          sections: [
            {
              title: 'Reportes',
              content: 'Crea reportes de sesiones, asistencias y progreso de pacientes.',
            },
          ],
        },
      },
      {
        route: '/therapist/analytics',
        content: {
          title: 'Analíticas IA',
          description: 'Análisis inteligente de sesiones y pacientes.',
          icon: ['fas', 'brain'],
          sections: [
            {
              title: 'Analíticas',
              content: 'Visualiza métricas avanzadas generadas por IA sobre el progreso de tus pacientes.',
              items: [
                'Gráficos de evolución por paciente.',
                'Recomendaciones basadas en el historial de sesiones.',
              ],
            },
          ],
        },
      },
      {
        route: '/therapist/calendar',
        content: {
          title: 'Calendario',
          description: 'Vista semanal de tus sesiones programadas.',
          icon: ['fas', 'calendar'],
          sections: [
            {
              title: 'Calendario',
              content: 'Visualiza tus sesiones en formato calendario semanal. Navega entre semanas.',
              items: [
                'Las sesiones aparecen con color según estado.',
                'Haz clic en una sesión para ver sus detalles.',
              ],
            },
          ],
        },
      },
      {
        route: '/therapist/games',
        content: {
          title: 'Juegos Terapéuticos',
          description: 'Accede a juegos educativos para usar con pacientes.',
          icon: ['fas', 'gamepad'],
          sections: [
            {
              title: 'Juegos',
              content: 'Selecciona un juego para usarlo durante la sesión con tu paciente.',
            },
          ],
        },
      },
      {
        route: '/therapist/profile',
        content: {
          title: 'Mi Perfil',
          description: 'Tu información personal.',
          icon: ['fas', 'user-circle'],
          sections: [
            {
              title: 'Perfil',
              content: 'Actualiza tus datos y cambia tu contraseña.',
            },
          ],
        },
      },
    ],
  },

  // ─── PATIENT / JUGADOR ──────────────────────────────────────────────
  {
    role: 'jugador',
    pages: [
      {
        route: '/patient/dashboard',
        content: {
          title: 'Mi Panel',
          description: 'Bienvenido a tu espacio personal.',
          icon: ['fas', 'home'],
          sections: [
            {
              title: 'Tu Panel',
              content: 'Aquí ves un resumen de tus sesiones, pagos y progreso general.',
              items: [
                'Revisa tus próximas sesiones en la tarjeta de eventos.',
                'Tu progreso general se muestra en la barra de avance.',
              ],
            },
          ],
          tips: [
            'Revisa "Mi Progreso" para ver tu evolución detallada.',
            'Comunícate con tu terapeuta desde Mensajes.',
          ],
        },
      },
      {
        route: '/patient/sessions',
        content: {
          title: 'Mis Sesiones',
          description: 'Historial y próximas sesiones de terapia.',
          icon: ['fas', 'calendar-alt'],
          sections: [
            {
              title: 'Sesiones',
              content: 'Visualiza tus sesiones programadas y completadas.',
              items: [
                'Las sesiones futuras muestran fecha, hora y modalidad.',
                'Las sesiones completadas incluyen notas del terapeuta.',
              ],
            },
          ],
        },
      },
      {
        route: '/patient/payments',
        content: {
          title: 'Mis Pagos',
          description: 'Control de tus pagos y plan de financiamiento.',
          icon: ['fas', 'wallet'],
          sections: [
            {
              title: 'Pagos',
              content: 'Revisa tu plan de pago, historial de pagos y estado de cuenta.',
              items: [
                'Tu plan actual muestra monto, fecha de vencimiento y forma de pago.',
                'El historial muestra todos los pagos registrados.',
              ],
            },
          ],
        },
      },
      {
        route: '/patient/progress',
        content: {
          title: 'Mi Progreso',
          description: 'Evolución de tu terapia.',
          icon: ['fas', 'chart-line'],
          sections: [
            {
              title: 'Progreso',
              content: 'Gráficos y métricas que muestran tu avance en las sesiones de terapia.',
              items: [
                'Asistencia: sesiones asistidas vs. programadas.',
                'Evolución por período.',
              ],
            },
          ],
        },
      },
      {
        route: '/patient/calendar',
        content: {
          title: 'Calendario',
          description: 'Tus sesiones programadas en vista calendario.',
          icon: ['fas', 'calendar'],
          sections: [
            {
              title: 'Calendario',
              content: 'Visualiza cuándo tienes sesiones programadas.',
            },
          ],
        },
      },
      {
        route: '/patient/messages',
        content: {
          title: 'Mensajes',
          description: 'Comunicación con tu terapeuta.',
          icon: ['fas', 'envelope'],
          sections: [
            {
              title: 'Chat',
              content: 'Conversa con tu terapeuta asignado. Los mensajes son en tiempo real.',
              items: [
                'Tu terapeuta responderá durante su horario laboral.',
                'Puedes adjuntar archivos si es necesario.',
              ],
            },
          ],
        },
      },
      {
        route: '/patient/profile',
        content: {
          title: 'Mi Perfil',
          description: 'Tus datos personales.',
          icon: ['fas', 'user-circle'],
          sections: [
            {
              title: 'Perfil',
              content: 'Revisa y actualiza tus datos personales.',
            },
          ],
        },
      },
      {
        route: '/patient/my-therapist',
        content: {
          title: 'Mi Terapeuta',
          description: 'Información de tu terapeuta asignado.',
          icon: ['fas', 'user-md'],
          sections: [
            {
              title: 'Terapeuta',
              content: 'Aquí ves los datos de contacto y especialidad de tu terapeuta.',
            },
          ],
        },
      },
    ],
  },
];
