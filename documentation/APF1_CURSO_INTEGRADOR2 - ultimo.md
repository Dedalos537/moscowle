“Año de la recuperación y consolidación de la economía peruana”

AVANCE DE PROYECTO FINAL 1

Curso:   Curso Integrador II: Sistemas

Docente:

Luis Gonzaga Neira Ayala

Integrantes:

•  Centeno Barrutia, Diego Barrutia

•  Peña Moran, Benjamín Esteban

•  Prieto Prieto, Oscar Eduardo

Piura, 2026

ÍNDICE

1. Contexto y Análisis Empresarial ............................................................................. 1

1.1. Arquitectura del Negocio Actual (As-Is) .......................................................... 1

1.2. Oportunidad de Innovación .............................................................................. 3

1.3. Arquitectura Propuesta (To-Be) ........................................................................ 3

2. Ingeniería de Requerimientos y Planificación Ágil ............................................... 5

2.1. Requerimientos Funcionales Definidos........................................................... 5

2.2. Requerimientos No Funcionales Definidos ..................................................... 6

2.3. Product Backlog Priorizado (MoSCoW) ........................................................... 7

2.2. Historias de Usuario y Criterios de Aceptación (BDD) ................................... 9

a) HU-S0-01: Definición del problema y propuesta de solución tecnológica .......... 9

b) HU-S0-02: Identificación de riesgos y plan de contingencia ............................. 10

c) HU-S0-03: Definición de KPIs del sistema ......................................................... 11

d) HU-S0-04: Diseño de wireframes ...................................................................... 11

e) HU-01: Registro de paciente desde el sistema ................................................. 12

f) HU-02: Autenticación de usuarios por rol con JWT ........................................... 12

g) HU-03: Gestión del perfil clínico del paciente ................................................... 13

h) HU-04: Gestión de programación de citas ........................................................ 14

i) HU-05: Carga del plan de sesión antes de la cita .............................................. 14

j) HU-06: Extracción automática de objetivos terapéuticos con LLaMA 3 ............. 15

k) HU-07: Grabación de audio de la sesión con micrófono lavalier ...................... 16

l) HU-08: Transcripción del audio con timestamps y eliminación del archivo ........ 16

m) HU-09: Comparación semántica entre sesión ejecutada y plan terapéutico ... 17

n) HU-10: Generación del reporte de auditoría por sesión ................................... 17

o) HU-13: Generación automática del informe de progreso .................................. 18

p) HU-15: Consulta del informe de progreso por el padre desde la app ............... 19

2.3. Gestión del Calendario (Gantt) y Scrum: Mapeo de los Sprints frente a los
hitos del ciclo .......................................................................................................... 19

2.3.1. Definición de los Sprints .......................................................................... 19

2.3.2. Diagrama de Gantt .................................................................................... 25

3.- Arquitectura y Gestión del Entorno de Desarrollo ............................................. 25

3.1. Infraestructura y Plataforma Cloud: Definición del entorno (IaaS,
PaaS,Contenedores). .............................................................................................. 25

3.2. Selección de Stack Tecnológico. .................................................................... 26

3.3. Gobernanza del Código ............................................................................... 26

4. Diseño de Interfaz y Estrategia de Rendimiento ................................................. 27

4.1. Wireframes y Mockups Interactivos ............................................................... 27

4.1.1. Pantalla de Autenticación ............................................................................ 27

4.1.2. Dashboard del Director ............................................................................... 27

4.1.3. Dashboard del Terapista .............................................................................. 29

4.1.4. Módulo de Gestión de Pacientes ................................................................ 30

4.1.5. Vista de Sesiones del Terapista .................................................................. 31

4.2. Heurísticas de Usabilidad ............................................................................... 31

4.2.1. Visibilidad del Estado del Sistema ............................................................... 31

4.2.2. Coincidencia entre el Sistema y el Mundo Real .......................................... 31

4.2.3. Control y Libertad del Usuario ..................................................................... 32

4.2.4. Prevención de Errores ................................................................................. 32

4.2.5. Reconocimiento antes que Recuerdo ......................................................... 32

4.3. Estrategia de Rendimiento Web (WPO) ............................................................ 33

4.3.1. Carga Diferida de Módulos .......................................................................... 33

4.3.2. Optimización de Imágenes y Recursos Estáticos ....................................... 33

4.3.3. Gestión de Estado y Reducción de Llamadas al Backend .......................... 33

4.3.4. Compresión y Configuración del Servidor ................................................... 33

5. Acuerdos de Niveles de Servicio (SLA) ................................................................ 34

5.1. Definición de Indicadores: KPIs operativos del sistema: ............................ 34

5.1.1. Índice de Cobertura del Plan de Sesión ...................................................... 34

5.1.2. Tiempo de Intervención Docente vs. Participación del Alumno ................... 34

5.1.3. Densidad de Conceptos Clave por Sesión .................................................. 34

5.1.4. Tasa de Precisión de la IA ........................................................................... 34

5.1.5. Tasa de Cumplimiento de Sesiones Programadas ...................................... 35

5.1.6. Índice de Satisfacción de Sesión ................................................................ 35

5.2 SLAs del Proyecto: Tiempos de respuesta y disponibilidad prometida. .... 35

5.2.1. Disponibilidad del Sistema .......................................................................... 35

5.2.2. Tiempos de Respuesta por Endpoint .......................................................... 36

5.2.3. Tiempos por Operación Crítica .................................................................... 36

5.2.4. SLAs de Reportes ....................................................................................... 36

5.2.5. Recuperación ante Fallos ............................................................................ 37

5.2.6. Escalamiento ante Violaciones .................................................................... 37

6. Gestión de Riesgos ................................................................................................ 37

6.1. Matriz de Riesgos: Riesgos del proyecto (retrasos) y riesgos técnicos
(caídas de servidor, pérdida de datos). ................................................................ 37

6.2. Plan de Mitigación: Acciones preventivas y correctivas. ............................ 39

6.2.1.

R01 — Incompatibilidad de entornos .................................................... 39

6.2.2.

6.2.3.

6.2.4.

6.2.5.

6.2.6.

R02 — Saturación de recursos por LLaMA y almacenamiento de audios
39

R03 — Precisión insuficiente de Whisper ............................................. 39

R04 — Fallo del micrófono lavalier ....................................................... 39

R05 — Interpretación incorrecta de momentos de clase por LLaMA ... 40

R06 — Privacidad de audios con voces de menores ........................... 40

7. Retrospectiva Sprint 2 y Evidencias ....................... ¡Error! Marcador no definido.

7.1. Análisis de Iteración: Cumplimiento de las Semanas Previas ............. ¡Error!
Marcador no definido.

7.2. Evidencias de Trabajo Grupal. .......................... ¡Error! Marcador no definido.

1. Contexto y Análisis Empresarial (BENJAMIN)

1.1. Arquitectura del Negocio Actual (As-Is)

El Centro de Terapias Juan Pablo II lleva más de dos décadas atendiendo a niños

y jóvenes con habilidades diferentes en nuestra región Piura. Su enfoque está orientado

a  principales  condiciones  como  el  autismo,  TDA,  TDAH  y  síndrome  de  Down,  entre

otras,  trabajando  con  cada  paciente  de  forma  individual  a  través  de  sesiones

planificadas por uno de sus terapistas asignados. Es importante señalar que la empresa

del trabajo se adapta semana a semana según el avance y la condición particular de

cada  niño,  con  una  revisión  formal  al  cierre  de  cada  bloque  de  cuatro  semanas,  las

cuales son clave para ver si es que realmente han progresado o no.

Actualmente, este centro de terapias todos sus procesos de atención funcionan

prácticamente de manera manual.

•  Cuando una familia nueva llega al centro, completa una ficha de inscripción en

papel. Las citas se coordinan por llamada telefónica o WhatsApp.

•  Los terapistas elaboran sus planes de sesión en cuadernos o documentos Word

sin ningún sistema que pueda guardarlos de manera adecuada.

•  Al terminar cada sesión, anotan sus observaciones a mano, y al cierre del bloque

mensual redactan el informe de progreso del paciente también de forma manual,

muchas veces desde cero.

El punto más crítico de este flujo ocurre justo ahí, al finalizar la sesión. No existe

ningún mecanismo que permita verificar de forma objetiva si lo que el terapista ejecutó

durante  la  sesión  realmente  correspondió  con  lo  que  había  planificado.  Todo  queda

sujeto al criterio y la memoria del propio especialista.

1

Diagrama de Procesos AS - IS:

Fuente: Propia

Recuperado de: https://www.bizagi.com/es

2

1.2. Oportunidad de Innovación

El  problema  concreto  que  motiva  este  proyecto  es  la  falta  de  un  sistema  que

conecte lo planificado con lo realmente ejecutado en cada sesión de terapia. Esta brecha

genera consecuencias directas para los tres actores principales del centro de terapias.

El Especialista Líder no tiene forma de saber con certeza qué ocurrió dentro de

cada sesión sin preguntarle directamente al terapista.

Los terapistas, por su parte, no reciben ningún tipo de retroalimentación objetiva

sobre su propio desempeño, más allá de su propia evaluación.

Y los padres de familia, que son quienes más necesitan saber cómo avanza su

hijo, reciben información de forma tardía, resumida y completamente subjetiva.

A  esto  se  suma  que  toda  la  gestión  administrativa  del  centro,  desde  las

inscripciones hasta la coordinación de citas, sigue dependiendo de procesos manuales

que consumen tiempo y generan errores evitables.

Además, nuestro proyecto no solo va a digitalizar toda la gestión del centro de

terapias,  sino  que  también  introduce  inteligencia  artificial  como  una  herramienta  de

apoyo real al trabajo terapéutico. No se trata de reemplazar al terapista, sino de darle

un respaldo objetivo que hoy no existe: saber con evidencia concreta qué funcionó en

cada sesión, qué quedó pendiente y cómo va evolucionando cada paciente semana a

semana, para ir junto de la mano porque Juan Pablo II busca la excelencia y calidad de

servicio con sus pacientes.

1.3. Arquitectura Propuesta (To-Be)

La  propuesta  de  solución  es  un  sistema  al  que  hemos  llamado  EduSync AI,

adaptado al contexto del centro de terapias.

Como  se  muestra  en  el  diagrama  To-Be,  la  implementación  de  este  sistema

cambia de fondo la forma en que opera el centro.

Las inscripciones y la gestión de citas pasan a manejarse desde una plataforma

web. Las notificaciones a los padres se vuelven automáticas.

El terapista carga digitalmente su plan de sesión antes de cada cita, y durante la

sesión el sistema graba el audio mediante un micrófono lavalier. Ese audio es transcrito

y procesado por el motor de inteligencia artificial basado en LLaMA 3, que lo compara

con el plan de sesión cargado previamente y genera un reporte de cumplimiento con

evidencia concreta.

El resultado de ese análisis se muestra en el dashboard del terapista y en la app

que usan los padres, quienes por primera vez pueden ver un resumen claro y objetivo

de lo que ocurrió en la sesión de su hijo. El Especialista Líder, a su vez, gana visibilidad

real  sobre  el  desempeño  del  centro  sin  depender  de  reportes  manuales  ni  de  la

percepción subjetiva de cada terapista.

3

Diagrama de Procesos TO - BE

Fuente: Propia

Recuperado

4

2. Ingeniería de Requerimientos y Planificación Ágil (BENJAMIN)

2.1. Requerimientos Funcionales Definidos

Tabla 1:

Requerimientos Funcionales Definidos

Cód.

RF-01

Descripción

Como  padre  de  familia,  quiero  registrar  a  mi  hijo  en  el  sistema

ingresando sus datos personales y condición clínica.

RF-02

Como usuario, quiero iniciar sesión con mis credenciales y acceder

a las funciones habilitadas para mi rol especifico.

RF-03

Como administrador, quiero registrar y gestionar los perfiles de los

terapistas.

RF-04

Como  administrador,  quiero  modificar  y  desactivar  cuentas  de

usuarios registrados en el sistema.

RF-05

Como terapista, quiero buscar y consultar el perfil clínico completo

de un paciente asignado a mis sesiones.

RF-06

Como terapista, quiero registrar y editar los datos clínicos de cada

paciente según su condición y el avance.

RF-07

Como  terapista,  quiero  programar  citas  para  mis  pacientes

seleccionando fecha y un horario disponible.

RF-08

Como terapista, quiero ver mi horario de citas organizadas en el

día a día.

RF-09

Como  sistema,  quiero  enviar  una  notificación  automática  de

confirmación de cita al padre de familia.

RF-10

Como terapista, quiero registrar la asistencia del paciente antes de

iniciar  cada  sesión  indicando  si  está  Presente,  Ausente  o  con

Tardanza.

RF-11

Como terapista, quiero subir el plan de sesión en formato PDF o

WORD antes de cada cita para que el sistema lo procese.

RF-12

Como  sistema,  quiero  extraer  automáticamente  los  objetivos

terapéuticos del plan de sesión cargado usando LLaMA 3.

RF-13

Como terapista, quiero iniciar y detener la grabación de audio de

la sesión desde el sistema.

RF-14

Como sistema, quiero transcribir el audio de la sesión con marcas

de tiempo por segmento usando LLaMA 3.

5

RF-15

Como sistema, quiero comparar semánticamente la transcripción

de la sesión con el plan cargado y clasificar cada objetivo como

Logrado, Más o menos; o No cubierto.

RF-16

Como sistema, quiero calcular el índice de cumplimiento global de

cada sesión a partir de la comparación semántica realizada.

RF-17

Como  sistema,  quiero  generar  reportes  de  análisis  para  cada

sesión analizada.

RF-18

Como  terapista,  quiero  visualizar  en  mi  dashboard  el  reporte  de

auditoría de cada sesión con gráficos y acceso a evidencias.

RF-19

Como  sistema,  quiero  generar  automáticamente  el  informe  de

progreso del paciente al cierre de cada bloque de 4 semanas.

RF-20

Como padre de familia, quiero descargar el informe de progreso

de mi hijo en formato PDF desde el sistema.

RF-21

Como terapista, quiero acceder al historial completo de sesiones y

reportes de un paciente para verificar su evolución.

RF-22

Como  administrador,  quiero  visualizar  el  dashboard  general  del

centro con los Kpis de todos los terapistas.

2.2. Requerimientos No Funcionales Definidos

Tabla 2:

Requerimientos No Funcionales

Cód.

Tipo

Descripción

RNF-01

Seguridad de datos  Como usuario, quiero que los datos clínicos estén

protegidos  en  todo  momento,  tanto  cuando  se

guardan  como  cuando  se  envían,  para  evitar

accesos no autorizados.

RNF-02

Privacidad del

Como  usuario,  quiero  que  el  sistema  elimine  el

paciente

archivo  de  audio  definitivamente  tras  confirmar

que

la

transcripción

fue

almacenada

correctamente.

RNF-03

Visibilidad del

Como usuario, quiero que el sistema me informe

estado del sistema

en todo momento el estado del procesamiento del

audio y la generación del reporte de auditoría.

6

RNF-04

Rendimiento

Como usuario, quiero que el reporte de auditoría

esté disponible en el dashboard en un máximo de

15 min tras finalizar la sesión.

RNF-05

Disponibilidad

Como  usuario,  quiero  que  el  sistema  esté

disponible durante todo el horario de atención del

centro sin interrupciones.

RNF-06

Consistencia y

Como  usuario,  quiero  que  el  sistema  mantenga

Accesibilidad

una

interfaz  uniforme  con

íconos  claros  y

RNF-07

Prevención de

Como  usuario,  quiero  que  el  sistema  bloquee

navegación coherente en todas las vistas.

errores

acciones  críticas  como  iniciar  la  grabación  sin

haber registrado previamente la asistencia.

RNF-08

Diseño

Como usuario, quiero que el sistema sea intuitivo

y visualmente ordenado con interfaz responsiva.

2.3. Product Backlog Priorizado (MoSCoW)

El Product Backlog está ordenado por prioridad de negocio, no por sprint. Para

la priorización, se utiliza la técnica MoSCoW:

•  Must Have (M): Debe tener

•  Should Have (S): Debería tener

•  Could Have (C): Podría tener

•  Won't Have (W): No tendrá

Tabla 3:

Product Backlog Priorizado

ID

Historia de Usuario

Tipo

Prioridad

HU-S0-01  Como equipo, quiero definir el problema central

Gestión

M

del centro de terapias y proponer una solución

tecnológica, para tener la idea clara del sistema

a desarrollar.

HU-S0-02  Como  equipo,  quiero  identificar  los  riesgos  del

Gestión

M

desarrollo,  para  contar  con  un  plan  de

contingencia ante posibles problemas.

7

HU-S0-03  Como  equipo,  quiero  definir

los  KPIs  del

Gestión

M

sistema, para medir objetivamente que tan bien

va el sistema.

HU-S0-04  Como equipo, quiero diseñar los wireframes de

Gestión

M

la plataforma web y la app móvil, para tener un

bosquejo visual antes de iniciar el desarrollo.

HU-01

Como padre de familia, quiero registrar a mi hijo

Funcional

M

desde el sistema, para evitar todo lo manual.

HU-02

Como  usuario,  quiero  iniciar  sesión  con  mis

Funcional

M

credenciales  y  acceder  solo  a  mi  rol,  para

garantizar la seguridad de la información.

HU-03

Como terapista, quiero gestionar el perfil clínico

Funcional

M

de  cada  paciente  asignado,  para  tener  una

mejor información.

HU-04

Como terapista, quiero programar citas desde la

Funcional

M

agenda  digital,  para  reemplazar  las  citas  vía

WhatsApp.

HU-05

Como terapista, quiero subir mi plan de sesión

Funcional

M

en PDF o WORD antes de cada cita, para que el

sistema extraiga los objetivos terapéuticos.

HU-06

Como sistema, quiero extraer automáticamente

Funcional

M

los  objetivos  terapéuticos  del  plan  de  sesión,

para  no  requerir

intervención  manual  del

terapista.

HU-07

Como terapista, quiero iniciar la grabación de la

Funcional

M

sesión  desde  la  app  con  el  micrófono  lavalier,

para capturar el audio completo de la terapia.

HU-08

Como  sistema,  quiero  transcribir  el  audio  y

Funcional

M

eliminarlo  después,  para  mantener  un  registro

de la sesión sin comprometer la privacidad del

paciente.

HU-09

Como sistema, quiero comparar la transcripción

Funcional

M

con el plan de sesión, para determinar el índice

de cumplimiento de cada objetivo terapéutico.

8

HU-10

Como  sistema,  quiero  generar  un  reporte  de

Funcional

M

auditoría  con  evidencias,  para  documentar

correctamente lo ejecutado en cada sesión.

HU-11

Como terapista, quiero ver en mi dashboard los

Funcional

M

objetivos logrados, parciales y pendientes, para

ajustar  mi  planificación  en

las  siguientes

sesiones.

HU-12

Como terapista, quiero marcar la asistencia del

Funcional

M

paciente  desde  el  sistema,  para  mantener  un

registro ordenado.

HU-13

Como  sistema,  quiero  generar  el  informe  de

Funcional

M

progreso al cierre del bloque de 4 semanas, para

reducir la redacción manual del terapista.

HU-14

Como  terapista,  quiero  revisar  y  aprobar  el

Funcional

M

informe de progreso antes de enviarlo al padre,

para validar que la información generada por la

IA es correcta

HU-15

Como padre de familia, quiero recibir el informe

Funcional

M

de progreso del bloque en la app con gráficos de

evolución, para entender el avance de mi hijo

HU-16

Como sistema, quiero implementar encriptación

No

M

AES-256  en  reposo  y  TLS  en  tránsito,  para

Funcional

garantizar la seguridad de los datos clínicos de

los pacientes

2.2. Historias de Usuario y Criterios de Aceptación (BDD)

a) HU-S0-01: Definición del problema y propuesta de solución tecnológica

Tabla 4:

HU-S0-01

Nombre historia: Definición del problema y propuesta de solución tecnológica

Prioridad en negocio: Alta

Riesgo en desarrollo: Baja

Estado: Completada

9

Descripción:

Como equipo, quiero definir el problema central del centro de terapias y proponer una solución

tecnológica, para tener la idea clara del sistema a desarrollar.

Criterio de aceptación:

GIVEN  el  equipo  identificó  que  el  centro  no  cuenta  con  un  mecanismo  que  conecte  lo

planificado con lo ejecutado en cada sesión

WHEN  se  elaboran  los  diagramas As-Is  y To-Be  en  Bizagi  y  se  define  el  stack  tecnológico

THEN  el  equipo  cuenta  con  la  arquitectura  del  negocio  documentada  y  la  propuesta  de

solución redactada.

b) HU-S0-02: Identificación de riesgos y plan de contingencia

Tabla 5:

HU-S0-02

Nombre historia: Identificación de riesgos y plan de contingencia

Prioridad en negocio: Alta

Riesgo en desarrollo: Baja

Estado: Completada

Descripción:

Como  equipo,  quiero  identificar  los  riesgos  del  desarrollo,  para  contar  con  un  plan  de

contingencia ante posibles problemas.

Criterio de aceptación:

GIVEN el equipo tiene definido el alcance del sistema y las tecnologías a utilizar

WHEN se identifican y clasifican todos los riesgos y sus categorías (Desarrollo, despliegue,

etc.) en la matriz de riesgos

THEN cada riesgo queda registrado con su nivel de probabilidad, impacto, estrategia, plan de

acción y el responsable.

10

c) HU-S0-03: Definición de KPIs del sistema

Tabla 6:

HU-S0-03

Nombre historia: Definición de KPIs del sistema

Prioridad en negocio: Media

Riesgo en desarrollo: Baja

Estado: Completada

Descripción:

Como equipo, quiero definir los KPIs del sistema, para medir objetivamente que tan bien va el

sistema.

Criterio de aceptación:

GIVEN  el  equipo  tiene  definidos  las  actividades  principales  del  sistema  y  sus  objetivos  de

negocio

WHEN se establecen los indicadores clave de desempeño para el motor de auditoría IA y los

módulos administrativos

THEN cada KPI queda redactado y verificado por el docente.

d) HU-S0-04: Diseño de wireframes

Tabla 7:

 HU-S0-04

Nombre historia: Diseño de wireframes de la plataforma

Prioridad en negocio: Media

Riesgo en desarrollo: Baja

Estado: Completada

Descripción:

Como equipo, quiero diseñar los wireframes de la plataforma web y la app móvil, para tener

un bosquejo visual antes de iniciar el desarrollo.

11

Criterio de aceptación:

GIVEN el equipo tiene definidos los módulos, roles de usuario y flujos principales del sistema

WHEN se diseñan los wireframes del dashboard web de los diferentes usuarios.

THEN los wireframes cubren los flujos principales del sistema y son verificados por el equipo

antes de la exposición del avance 1.

e) HU-01: Registro de paciente desde el sistema

Tabla 8:

HU-01

Nombre historia: Registro de paciente desde el sistema

Prioridad en negocio: Alta

Riesgo en desarrollo: Baja

Estado: Pendiente

Descripción:

Como padre de familia, quiero registrar a mi hijo desde el sistema, para evitar todo lo manual.

Criterio de aceptación:

GIVEN el padre tiene sesión activa en la app y el paciente no existe en el sistema

WHEN completa todos los campos obligatorios del formulario de registro y presiona "Registrar"

THEN el sistema guarda los datos del paciente, genera un ID único y muestra un mensaje de:

"Paciente registrado exitosamente"

f) HU-02: Autenticación de usuarios por rol con JWT

Tabla 9:

HU-02

Nombre historia: Autenticación de usuarios por rol con JWT

Prioridad en negocio: Alta

Riesgo en desarrollo: Baja

Estado: Pendiente

12

Descripción:

Como  usuario,  quiero  iniciar  sesión  con  mis  credenciales  y  acceder  solo  a  mi  rol,  para

garantizar la seguridad de la información.

Criterio de aceptación:

GIVEN el usuario tiene una cuenta activa con rol asignado en el sistema

WHEN ingresa su email y contraseña y presiona el botón de "Iniciar sesión"

THEN  el  sistema  valida  el  token  JWT,  identifica  el  rol  del  usuario  y  redirige  al  dashboard

correspondiente según sus accesos.

g) HU-03: Gestión del perfil clínico del paciente

Tabla 10:

 HU-03

Nombre historia: Gestión del perfil clínico del paciente

Prioridad en negocio: Alta

Riesgo en desarrollo: Baja

Estado: Pendiente

Descripción:

Como terapista, quiero gestionar el perfil clínico de cada paciente asignado, para tener una

mejor información.

Criterio de aceptación:

GIVEN el terapista se encuentra en el sistema y accede al módulo de gestión de pacientes

WHEN busca un paciente ingresando su DNI registrado en el sistema

THEN el sistema muestra los datos clínicos del paciente, su historial de citas y la información

del familiar a su cargo.

13

h) HU-04: Gestión de programación de citas

Tabla 11:

HU-04

Nombre historia: Gestión de programación de citas

Prioridad en negocio: Alta

Riesgo en desarrollo: Medio

Estado: Pendiente

Descripción:

Como terapista, quiero programar citas desde la agenda digital, para reemplazar las citas vía

WhatsApp.

Criterio de aceptación:

GIVEN  el  terapista  está  en  el  módulo  de  agenda  y  selecciona  un  paciente  y  un  horario

disponible

WHEN confirma la cita en el sistema

THEN el sistema registra la cita en la base de datos y envía automáticamente una notificación

de confirmación al padre en el sistema.

i) HU-05: Carga del plan de sesión antes de la cita

Tabla 12:

HU-05

Nombre historia: Carga del plan de sesión antes de la cita

Prioridad en negocio: Alta

Riesgo en desarrollo: Medio

Estado: Pendiente

Descripción:

Como terapista, quiero subir mi plan de sesión en PDF o WORD antes de cada cita, para que

el sistema extraiga los objetivos terapéuticos.

14

Criterio de aceptación:

GIVEN  el  terapista  tiene  una  cita  programada  para  ese  día  y  selecciona  un  archivo  PDF  o

WORD de hasta 10MB

WHEN presiona "Subir plan de sesión"

THEN  el  sistema  valida  el  formato  y  tamaño,  almacena  el  documento  vinculado  a  la  cita  y

confirma la carga mostrando el nombre del archivo registrado.

j) HU-06: Extracción automática de objetivos terapéuticos con LLaMA 3

Tabla 13:

HU-06

Nombre historia: Extracción automática de objetivos terapéuticos con LLaMA 3

Prioridad en negocio: Alta

Riesgo en desarrollo: Alto

Estado: Pendiente

Descripción:

Como sistema, quiero extraer automáticamente los objetivos terapéuticos del plan de sesión,

para no requerir intervención manual del terapista.

Criterio de aceptación:

GIVEN el terapista subió exitosamente el plan de sesión y el documento contiene texto legible

WHEN LLaMA 3 procesa el contenido del documento con el prompt de extracción

THEN el sistema muestra al terapista la lista de objetivos terapéuticos identificados y le permite

validarlos antes de iniciar la sesión.

15

k) HU-07: Grabación de audio de la sesión con micrófono lavalier

Tabla 14:

HU-07

Nombre historia: Grabación de audio de la sesión con micrófono lavalier

Prioridad en negocio: Alta

Riesgo en desarrollo: Alto

Estado: Pendiente

Descripción:

Como terapista, quiero iniciar la grabación de la sesión desde la app con el micrófono lavalier,

para capturar el audio completo de la terapia.

Criterio de aceptación:

GIVEN el terapista registró la asistencia del paciente, cargó el plan de sesión y el micrófono

lavalier está conectado al dispositivo

WHEN presiona "Iniciar grabación" en el sistema

THEN el sistema activa el micrófono, muestra el indicador de grabación en curso con el tiempo

transcurrido y almacena el audio temporalmente en el servidor.

l) HU-08: Transcripción del audio con timestamps y eliminación del archivo

Tabla 15:

HU-08

Nombre historia: Transcripción del audio con timestamps y eliminación del archivo

Prioridad en negocio: Alta

Riesgo en desarrollo: Alto

Estado: Pendiente

Descripción:

Como sistema, quiero transcribir el audio y eliminarlo después, para mantener un registro de

la sesión sin comprometer la privacidad del paciente.

16

Criterio de aceptación:

GIVEN el terapista detuvo la grabación y el archivo de audio fue recibido correctamente por el

servidor

WHEN LLaMA 3 procesa el audio y genera la transcripción completa con timestamps

THEN el sistema almacena la transcripción en la BD vinculada a la sesión y elimina el archivo

de audio de forma inmediata del servidor.

m) HU-09: Comparación semántica entre sesión ejecutada y plan terapéutico

Tabla 16:

HU-09

Nombre historia: Comparación semántica entre sesión ejecutada y plan terapéutico

Prioridad en negocio: Alta

Riesgo en desarrollo: Alto

Estado: Pendiente

Descripción:

Como  sistema,  quiero  comparar  la  transcripción  con  el  plan  de  sesión,  para  determinar  el

índice de cumplimiento de cada objetivo terapéutico.

Criterio de aceptación:

GIVEN existen una transcripción y un plan de sesión almacenados y vinculados a la misma

cita

WHEN LLaMA 3 ejecuta la comparación semántica entre ambos documentos

THEN el sistema clasifica cada objetivo como Logrado, Parcial o No cubierto, calcula el índice

de cumplimiento global y almacena los resultados.

n) HU-10: Generación del reporte de auditoría por sesión

Tabla 17:

 HU-10

Nombre historia: Generación del reporte de auditoría por sesión

17

Prioridad en negocio: Alta

Riesgo en desarrollo: Medio

Estado: Pendiente

Descripción:

Como  sistema,  quiero  generar  un  reporte  de  auditoría  con  evidencias,  para  documentar

correctamente lo ejecutado en cada sesión.

Criterio de aceptación:

GIVEN el motor de comparación semántica completó el análisis y todos los objetivos fueron

clasificados

WHEN el sistema estructura los resultados del análisis en el reporte

THEN  genera  el  reporte  completo  con  índice  de  cumplimiento,  objetivos  clasificados  y

evidencias, almacenado y vinculado a la sesión en la base de datos

o) HU-13: Generación automática del informe de progreso

Tabla 18:

HU-13

Nombre historia: Generación automática del informe de progreso del bloque de 4 semanas

Prioridad en negocio: Alta

Riesgo en desarrollo: Alto

Estado: Pendiente

Descripción:

Como sistema, quiero generar el informe de progreso al cierre del bloque de 4 semanas, para

reducir la redacción manual del terapista.

Criterio de aceptación:

GIVEN el paciente completó las 4 semanas del bloque y todas las sesiones tienen reporte de

auditoría generado

WHEN el sistema detecta el cierre del bloque

18

THEN genera el informe comparando el estado inicial y final de cada objetivo terapéutico con

gráficos de evolución

p) HU-15: Consulta del informe de progreso por el padre desde la app

Tabla 19:

HU-15

Nombre historia: Consulta del informe de progreso por el padre desde la app

Prioridad en negocio: Alta

Riesgo en desarrollo: Bajo

Estado: Pendiente

Descripción:

Como padre de familia, quiero recibir el informe de progreso del bloque en la app con gráficos

de evolución, para entender el avance de mi hijo.

Criterio de aceptación:

GIVEN el terapista aprobó el informe de progreso del bloque y el padre tiene la app instalada

con notificaciones habilitadas

WHEN el sistema confirma la aprobación del informe

THEN envía una notificación al padre y publica el informe en la app con gráficos de evolución

y la comparativa de objetivos entre el inicio y el cierre del bloque de 4 semanas.

2.3. Gestión del Calendario (Gantt) y Scrum: Mapeo de los Sprints frente a los hitos

del ciclo

2.3.1. Definición de los Sprints

Sprint 0 : Definición y Planificación del Proyecto (Semanas 1-5 del ciclo: 24 marzo

– 22 abril)

Este  sprint  representa  toda  la  fase  inicial  del  proyecto.  Las  HU  aquí  no  son

funcionalidades del sistema, sino entregables académicos del equipo.

19

Tabla 20:

Sprint Backlog 0

Cód.

HU

Tareas

Estados

HU-S0-01

Definición del

Analizar  el  proceso  actual  del  centro

COMPLETADA

problema y propuesta

(As-Is) y elaborar el diagrama en Bizagi

de solución

Definir la arquitectura propuesta (To-Be)

COMPLETADA

tecnológica

y elaborar el diagrama en Bizagi

Seleccionar las tecnologías del stack

COMPLETADA

Identificar la idea central del sistema

COMPLETADA

HU-S0-02

Identificación de

Identificar  riesgos  técnicos  de  acuerdo

COMPLETADA

riesgos y plan de

con

su

clasificación

(despliegue,

contingencia

desarrollo, etc.)

Clasificar cada riesgo por probabilidad e

COMPLETADA

impacto (matriz de riesgos)

Definir plan de acción para cada riesgo

COMPLETADA

crítico identificado

Documentar la matriz en el informe 1

COMPLETADA

HU-S0-03  Definición de KPIs del

Definir  los  KPIs  del  motor  de  auditoría

COMPLETADA

sistema

IA

Definir  KPIs  operativos  del  dashboard

COMPLETADA

general

Establecer

los

valores  mínimos

COMPLETADA

aceptables para cada indicador

Documentar  los  KPIs  en  el  informe

COMPLETADA

APF1

HU-S0-04

Diseño de wireframes  Diseñar  wireframes  del  dashboard  del

COMPLETADA

terapista

Diseñar wireframes de la app del padre

COMPLETADA

de familia

Diseñar  wireframes  del

flujo  de

COMPLETADA

grabación y carga del plan de sesión

Sprint 1: Gestión Base del Sistema (Registro, autenticación, perfiles y agenda)

Objetivo: Tener el sistema funcionando con sus módulos administrativos base:

los usuarios pueden registrarse, autenticarse y gestionar pacientes y citas.

20

Tabla 21:

Sprint Backlog 01

Cód.

HU

Tareas

Estados

HU-01

Registro de paciente

Diseñar  formulario  de  inscripción  con

PENDIENTE

desde el sistema

validación de campos

Implementar  endpoint  de  registro  de

PENDIENTE

paciente

Generar  ID  único  por  paciente  en

PENDIENTE

PostgreSQL

Mostrar confirmación visual tras registro

PENDIENTE

exitoso

HU-02

Autenticación de

Implementar  autenticación  JWT  en

PENDIENTE

usuarios por rol con

Flask con roles definidos

JWT

Crear  vistas  diferenciadas  por

rol

PENDIENTE

(Terapista, padre, admin)

Configurar  expiración  automática  de

PENDIENTE

sesión por inactividad

HU-03

Gestión del perfil

Diseñar  modelo  de  datos  del  perfil

PENDIENTE

clínico del paciente

clínico en PostgreSQL

Implementar búsqueda de paciente por

PENDIENTE

DNI en el backend

Crear vista de perfil clínico con historial

PENDIENTE

de citas

Restringir visualización solo a pacientes

PENDIENTE

asignados al terapista en sesión

HU-04

Gestión de

Implementar  módulo  de  agenda  con

PENDIENTE

programación de citas

vista de calendario

Crear

lógica

de

validación

de

PENDIENTE

disponibilidad de horarios

Registrar cita en PostgreSQL vinculada

PENDIENTE

a terapista y paciente

21

Sprint 2: Motor de Captura y Transcripción (Carga del plan, grabación, transcripción

IA y privacidad)

Objetivo: El terapista puede cargar su plan de sesión, grabar la sesión con el

lavalier y obtener una transcripción automática generada por LLaMA 3.

Tabla 22:

Sprint Backlog 02

Cód.

HU

Tareas

Estados

HU-05

Carga del plan de

Implementar  endpoint  de  carga  de

PENDIENTE

sesión antes de la cita

archivos PDF y WORD en Flask

Validar  formato  y  tamaño  del  archivo

PENDIENTE

antes de almacenar (máx. 10MB)

Vincular el documento cargado al ID de

PENDIENTE

la cita en PostgreSQL

HU-06

Extracción automática

Diseñar  prompt  de  extracción  de

PENDIENTE

de objetivos

objetivos terapéuticos para LLaMA 3

terapéuticos con

Almacenar

objetivos

extraídos

PENDIENTE

LLaMA 3

vinculados a la cita en PostgreSQL

Mostrar  lista  de  objetivos  al  terapista

PENDIENTE

para validación antes de iniciar sesión

HU-07

Grabación de audio de

Implementar  módulo  de  grabación  de

PENDIENTE

la sesión con

audio en el sistema

micrófono lavalier

Configurar  transmisión  del  audio  al

PENDIENTE

servidor Flask

Almacenar el archivo de audio temporal

PENDIENTE

vinculado al ID de sesión

HU-08

Transcripción del

Integrar  motor  de

transcripción  de

PENDIENTE

audio con timestamps

LLaMA 3 en el backend Flask

y eliminación del

Generar

timestamps

por

cada

PENDIENTE

archivo

segmento de la transcripción

Almacenar

la

transcripción

en

PENDIENTE

PostgreSQL vinculada a la sesión

22

Sprint 3: Motor de Auditoría IA (Comparación semántica, reportes y dashboards)

Objetivo: El sistema compara lo grabado con lo planificado, genera el reporte de

auditoría y lo presenta en el dashboard del terapista con evidencias concretas.

Tabla 23:

Sprint Backlog 03

Cód.

HU

Tareas

Estados

HU-09

Comparación

Diseñar  prompt  de

comparación

PENDIENTE

semántica entre

semántica para LLaMA 3

sesión ejecutada y

Implementar  clasificación  de  objetivos:

PENDIENTE

plan terapéutico

Logrado, Parcial, No cubierto

Calcular  índice  de  cumplimiento  global

PENDIENTE

por sesión

HU-10

Generación del

Implementar endpoint de generación de

PENDIENTE

reporte de auditoría

reporte en Flask

por sesión

Almacenar el reporte vinculado al ID de

PENDIENTE

sesión en la base de datos

Mostrar  mensaje  "en  proceso"  si  el

PENDIENTE

reporte aún no está disponible

HU-11

Dashboard del

Diseñar dashboard del terapista

PENDIENTE

terapista con

Implementar  filtrado  de  sesiones  por

PENDIENTE

resultados de

paciente en el dashboard

auditoría

Generar  alerta  visible  si  el  índice  de

PENDIENTE

cumplimiento es menor al 70%

HU-12

Registro de asistencia

Implementar  módulo  de  registro  de

PENDIENTE

del paciente por

asistencia vinculado a cada cita

sesión

Definir estados de asistencia: Presente,

PENDIENTE

Ausente, Tardanza

Bloquear  el  inicio  de  grabación  si  la

PENDIENTE

asistencia

no

fue

registrada

previamente

23

Sprint 4: Informes, App del Padre y Seguridad (Informe de bloque, vista del padre,

encriptación e historial)

Objetivo:  Generar  el  informe  de  4  semanas  automáticamente,  el  terapista  lo

aprueba, el padre lo recibe a través del sistema y este cumple con los estándares de

seguridad y privacidad.

Tabla 24:

Sprint Backlog 04

Cód.

HU-13

HU

Tareas

Estados

Generación

Implementar  lógica  de  detección  de

PENDIENTE

automática del informe

cierre de bloque en el backend

de progreso del

Consolidar

los

reportes  de

las  4

PENDIENTE

bloque de 4 semanas

sesiones del bloque para el informe

Generar  gráficos  de  evolución  por

PENDIENTE

objetivo terapéutico

HU-14

Revisión y aprobación

Crear vista de revisión y aprobación del

PENDIENTE

del informe de

informe

progreso por el

Implementar flujo de estados: borrador

PENDIENTE

terapista

- aprobado - publicado

Habilitar  edición  del  borrador  antes  de

PENDIENTE

la aprobación final

HU-15

Consulta del informe

Implementar  vista  del

informe  de

PENDIENTE

de progreso por el

progreso en el sistema

padre desde la app

Mostrar

gráficos

de

evolución

PENDIENTE

comparando inicio y cierre del bloque

Habilitar  descarga  del  informe  en  PDF

PENDIENTE

desde el sistema

HU-16

Encriptación de datos

Configurar  encriptación  AES-256  para

PENDIENTE

clínicos y seguridad

datos en reposo en PostgreSQL

del sistema

Implementar protocolo TLS en todas las

PENDIENTE

comunicaciones del sistema

Configurar

rechazo  automático  de

PENDIENTE

tokens JWT expirados o inválidos

24

2.3.2. Diagrama de Gantt

3.- Arquitectura y Gestión del Entorno de Desarrollo (OSCAR)

3.1. Infraestructura y Plataforma Cloud: Definición del entorno (IaaS,
PaaS,Contenedores).

Nuestra plataforma será alojada y gestionada en el servicio de hosting conocido

como  Cpanel,  evitando  múltiples  proovedores  para  un  ahorro  de  coste  bruto  del

proyecto,  centralizando  y  simplificando  su  desarrollo  sin  complicaciones  para

desenvolver sus capacidades necesarias para este sistema.

Flask  será  utilizado  como  backend  y  se  ejecuta  mediante  el  gestor  de

aplicaciones del mismo hosting especializado para Python, mientras tanto el frontend

desarrollado  en  el  Framework  de Angular  será  alojado  directamente  en  el  directorio

public_html  del  mismo.  Con  motor  de  base  de  datos,  se  hará  uso  del  PostgreSQL,

manejando la totalidad de los datos registrados del ERP y las sesiones de auditoría. Y

por  último,  en  lo  que  respecta  al  almacenamiento  del  audio,  se  utilizará  el  mismo  de

Cpanel pero de forma temporal, eliminando posteriormente de la transcripción realizada

por  la  IA,  de  manera  irreversible,  ayudando  a  resolver  un  requisito  importante  de

privacidad y evitando la dependencia de políticas externas de retención.

25

3.2. Selección de Stack Tecnológico.

El  stack  se  eligió  en  respuesta  a  cada  una  de  las  necesidades  concretas del

sistema,  evitando  preferencias  genéricas.  Se  tomó  la  elección  de  Angular  como

Framework  de  frontend  devido  a  la  diversidad  de  dashboards  distintos  (Terapista,

Paciente  y Administrador)  con  una  lógica  direrente  en  la  visualización  de  cada  uno.

Gracias  a  su  arquitectura  modular y  a  la  utilización  nativa  del  lenguaje TypeScript  se

maneja la complejidad del desarrollo, aligerando el mantenimiento y la escalabilidad con

un código amigable.

Posteriormente,  para  el  desarrollo  backend  se  escogió  Flask  a  causa  de  su

excelente gestión asíncrona de las llamadas a los modelos de IA utilizados para análisis

y  posetior  auditoría  de  sesiones,  y  la  modularidad  de  su  estructura  que  permite  la

incorporación de servicios complementarios (pagos, generar reportes, notificaciones).

Al mismo tiempo se tomó la decisión de usar PostgreSQL ya que la sensibilidad

de  los  datos  que  maneja  el  sistema  es  elevada  (registro  de  terapistas  y  pacientes),

priorizando la integridad referencial, y requiriendo un motor que no baje su rendimiento

con  el  tiempo  por  el  aumento  de  consultas  acerca  de  índices  de  cumplimiento

pedagógico o progreso terapéutico.

Por último, con respecto a los patrones de diseño utilizados, gracias a la forma

nativa de la inyección de dependencias de Angular y la arquitectura en capas que sigue

el backend con la separación lógica de negocio del acceso a datos, se agiliza el testeo

y modificación de distintas partes del sistema sin afectar al resto.

3.3. Gobernanza del Código

El repositorio en GitHub sigue la estrategia GitFlow. Cada sprint tiene su propia

rama,  la  convención  es  sprint-2,  sprint-3,  etc.,  y  el  trabajo  individual  se  organiza  en

ramas  feature  que  se  integran  por  pull  request.  Eso  evita  que  cambios  en  desarrollo

rompan lo que ya está en producción.

El  despliegue  se  automatiza  a  través  de  la  integración  Git  que  ofrece  cPanel:

cuando se hace push al branch de producción, el build de Angular y las actualizaciones

de Flask se despliegan sin intervención manual. Flask genera logs estructurados que

quedan  almacenados  en  cPanel  y  sirven  para  auditoría  y  debugging  cuando  hay

incidentes.

26

4. Diseño de Interfaz y Estrategia de Rendimiento (OSCAR)

4.1. Wireframes y Mockups Interactivos

4.1.1. Pantalla de Autenticación

La  pantalla  de  inicio  de  sesión  corresponde  a  la  puerta  de  entrada  única  al

sistema para los tres roles definidos: director, terapista y paciente. El diseño presenta

un  formulario  centrado  sobre  fondo  neutro,  con  el  logotipo  e  identidad  del  Centro  de

Terapias  Juan  Pablo  II  en  la  parte  superior.  Los  campos  de  correo  electrónico  y

contraseña siguen un orden vertical estándar, acompañados de iconos de apoyo que

refuerzan la función de cada campo sin necesidad de etiquetas adicionales. Se incluye

la  opción  de  recordar  sesión  y  un  enlace  de  recuperación  de  contraseña,  ambos

ubicados antes del botón de acción principal. El botón de inicio de sesión ocupa el ancho

completo del formulario, maximizando el área táctil en dispositivos móviles. La paleta

utiliza tonos verdes sobre blanco, coherente con la identidad visual del centro.

Figura 1. Mockup de pantalla de autenticación — Centro de Terapias Juan Pablo II.

4.1.2. Dashboard del Director

La vista principal del director presenta un saludo personalizado acompañado de

un resumen ejecutivo del estado del sistema en tiempo real. Tres tarjetas de indicadores

clave ocupan la parte superior: índice de cumplimiento general, sesiones activas del día

y  alertas  críticas  que  requieren  atención  inmediata.  Debajo,  un  gráfico  de  tendencias

semanales  permite  al  director  identificar  patrones  de  cumplimiento  a  lo  largo  de  los

27

últimos siete días con selector de vista temporal. La sección inferior muestra una tabla

de  estado  de  auditoría  por  terapista,  con  nombre,  curso  o  área  asignada,  estado  de

cumplimiento y acceso directo al detalle del reporte. La navegación lateral agrupa las

secciones  en  Teachers,  Students,  Courses,  Schedules  y  Audit  Reports,  con  acceso

global al generador de reportes desde el panel izquierdo.

Figura 2. Mockup de dashboard del director — vista de cumplimiento y auditoría en
tiempo real.

28

4.1.3. Dashboard del Terapista

La  vista  del  terapista  prioriza  la  jornada  del  día  como  elemento  central.  Un

encabezado dinámico indica la próxima sesión programada con nombre de la asignatura

y hora exacta. El módulo principal muestra la sesión activa en curso con porcentaje de

cobertura  del  contenido  planificado,  meta  semanal  y  desglose  de  temas  según  su

estado: logrado, parcial o pendiente. La columna derecha presenta la agenda del día

completa  en  formato  cronológico,  con  cada  bloque  identificado  por  materia,  aula  y

horario. En la parte inferior se disponen tres indicadores compactos: reportes pendientes

con nivel de prioridad, progreso académico mensual y acceso al módulo de IA Coach

con  sugerencias  activas.  La  navegación  lateral  replica  la  estructura  del  director,

adaptando las opciones al perfil del terapista.

Figura 3. Mockup de dashboard del terapista — resumen diario y seguimiento de
sesión activa.

29

4.1.4. Módulo de Gestión de Pacientes

El módulo de gestión de pacientes presenta una tabla paginada con identificador

único,  nombre  completo,  grado  y  sección,  contacto  del  apoderado  y  estado  de  pago

para cada registro. La barra superior combina un campo de búsqueda por nombre o DNI

con  dos  selectores  de  filtro  por  grado  y  sección,  más  un  botón  de  filtros  avanzados.

Cada fila incluye un enlace directo al perfil completo del paciente. En la parte inferior de

la  vista  se  disponen  tres  bloques  de  resumen:  total  de  estudiantes  matriculados  con

variación mensual, cantidad de pagos pendientes como porcentaje de la matrícula total,

y  acceso  al  generador  de  padrón  consolidado  en  formato  PDF  o  Excel.  El  botón  de

registro de nuevo alumno se ubica en la esquina superior derecha, fuera del área de la

tabla para evitar activaciones accidentales.

Figura 4. Mockup de módulo de gestión de pacientes — tabla, filtros y resumen de
matrícula.

30

4.1.5. Vista de Sesiones del Terapista

La vista de sesiones organiza la actividad clínica del terapista en dos zonas. La

zona superior muestra cuatro tarjetas de métricas globales: sesiones programadas para

el  día,  total  de  sesiones  completadas,  sesiones  con  estado  pendiente  y  número  de

pacientes activos. La zona central presenta un calendario mensual de navegación libre

donde los días con sesiones registradas muestran puntos indicadores de actividad. Al

seleccionar una fecha, la columna derecha despliega el detalle de cada sesión: hora,

nombre del paciente, bloque de trabajo y estado de completitud, con acceso directo a la

revisión  de  imágenes  o  materiales  asociados.  La  navegación  lateral  incluye  Panel,

Pacientes,  Ejercicios,  IA Analytics,  Sesiones,  Reportes  y  Mensajes,  cubriendo  el  flujo

completo de trabajo del terapista dentro de la plataforma.

Figura 5. Mockup de vista de sesiones — calendario mensual y detalle de sesiones por
fecha.

4.2. Heurísticas de Usabilidad

Las  decisiones  de  interfaz  del  sistema  se  fundamentan  en  los  diez  principios

heurísticos de Nielsen (1994), seleccionando aquellos de mayor impacto sobre los flujos

críticos identificados durante el análisis de requerimientos.

4.2.1. Visibilidad del Estado del Sistema

Cada vista mantiene al usuario informado sobre lo que ocurre en el sistema sin

necesidad  de  que  lo  solicite.  El  dashboard  del  director  muestra  el  índice  de

cumplimiento, las sesiones activas y las alertas críticas en tiempo real desde la primera

pantalla. El dashboard del terapista indica el porcentaje de cobertura de la sesión en

curso y el estado de cada tema del plan. Los estados de pago en la tabla de pacientes

utilizan etiquetas de color diferenciadas —verde para pagado, rojo para pendiente— que

comunican  la  situación  sin  requerir  lectura  del  texto.  Esta  decisión  responde

directamente al principio de visibilidad del estado, que establece que el sistema debe

mantener siempre informado al usuario sobre lo que ocurre, mediante retroalimentación

apropiada y en tiempo razonable (Nielsen, 1994).

4.2.2. Coincidencia entre el Sistema y el Mundo Real

El lenguaje utilizado en la interfaz corresponde al vocabulario propio del entorno

clínico  y  terapéutico.  Términos  como  sesión,  paciente,  terapista,  bloque  y  cobertura

forman parte del léxico habitual de los usuarios del sistema, evitando tecnicismos de

software que generarían fricción cognitiva. Los iconos de cada sección del menú lateral

31

refuerzan visualmente el significado de cada módulo: un ícono de grupo de personas

para pacientes, un calendario para sesiones y un gráfico para reportes. Nielsen (1994)

señala  que  el  sistema  debe  hablar  el  idioma  del  usuario,  con  palabras,  frases  y

conceptos familiares para él, en lugar del lenguaje orientado al sistema.

4.2.3. Control y Libertad del Usuario

La  navegación  lateral  permanece  visible  en  todas  las  vistas,  permitiendo  al

usuario moverse entre módulos sin depender del botón de retroceso del navegador. El

formulario  de  login  incluye  la  opción  de  recuperar  contraseña  sin  salir  de  la  pantalla

principal  de  acceso.  En  el  módulo  de  sesiones,  el  selector  de  fecha  del  calendario

permite navegar hacia adelante y atrás sin comprometer los datos ya cargados. Estos

elementos responden al principio que establece que los usuarios suelen elegir funciones

del sistema por error y necesitan salidas de emergencia claramente marcadas (Nielsen,

1994).

4.2.4. Prevención de Errores

El formulario de autenticación valida el formato del correo electrónico antes de

permitir el envío de la solicitud al servidor, evitando llamadas innecesarias al backend

por datos malformados. El botón de inicio de sesión permanece en estado deshabilitado

visualmente  mientras  los  campos  están  vacíos,  reduciendo  el  riesgo  de  envíos

accidentales.  En  el  módulo  de  gestión  de  pacientes,  el  botón  de  registro  de  nuevo

alumno se ubica fuera del área de la tabla para evitar activaciones por error durante la

navegación.  Nielsen  (1994)  sostiene  que  un  diseño  cuidadoso  que  previene  que  los

problemas ocurran es preferible a los buenos mensajes de error.

4.2.5. Reconocimiento antes que Recuerdo

Los  filtros  de  búsqueda  en  el  módulo  de  pacientes  presentan  opciones

predefinidas  mediante  selectores  desplegables,  eliminando  la  necesidad  de  que  el

usuario  recuerde  los  valores  posibles  para  cada  campo.  El  calendario  de  sesiones

marca  visualmente  los  días  con  actividad  registrada  mediante  puntos  indicadores,

permitiendo  identificar  de  un  vistazo  qué  fechas  tienen  contenido  sin  necesidad  de

navegar  por  cada  una.  La  tabla  de  auditoría  del  director  muestra  el  estado  de  cada

terapista  con  etiquetas  de  color  y  texto  simultáneamente,  reduciendo  la  carga  de

interpretación. Este principio establece que se deben minimizar la carga de memoria del

usuario haciendo visibles los objetos, acciones y opciones (Nielsen, 1994).

32

4.3. Estrategia de Rendimiento Web (WPO)

La  estrategia  de  rendimiento  web  define  las  prácticas  que  el  equipo  aplicará

durante la conversión de los mockups a código Angular para asegurar tiempos de carga

aceptables en el entorno de producción del Centro de Terapias Juan Pablo II.

4.3.1. Carga Diferida de Módulos

Angular  18  permite  configurar  la  carga  diferida  (lazy  loading)  de  módulos

mediante la definición de rutas con importación dinámica. Cada módulo del sistema —

pacientes, sesiones, reportes, IA Analytics— se cargará únicamente cuando el usuario

navegue hacia él, reduciendo el tamaño del bundle inicial de la aplicación. Esta práctica

impacta directamente sobre el tiempo hasta la primera interacción (Time to Interactive),

que  es  uno  de  los  indicadores  principales  del  rendimiento  percibido  por  el  usuario

(Google, 2023).

4.3.2. Optimización de Imágenes y Recursos Estáticos

Los recursos gráficos del sistema, incluyendo avatares de usuarios, íconos de

módulos y logotipos, se servirán en formato WebP con fallback a PNG para navegadores

sin soporte. Las imágenes se redimensionarán en el servidor antes de almacenarse en

AWS S3, evitando que el navegador descargue versiones de mayor resolución que la

necesaria  para  el  contexto  de  visualización.  Los

íconos  de  navegación  se

implementarán  como  fuente  de  íconos  o  SVG  inline  para  evitar  solicitudes  HTTP

adicionales por cada elemento gráfico.

4.3.3. Gestión de Estado y Reducción de Llamadas al Backend

El  sistema  implementará  un  servicio  de  caché  en  memoria  dentro  de Angular

para almacenar temporalmente las respuestas de los endpoints de mayor frecuencia de

consulta,  como  el  listado  de  pacientes  y  el  calendario  de  sesiones.  Las  peticiones  al

backend Flask se agruparán cuando sea posible para reducir el número de roundtrips

por vista. Los datos del dashboard del terapista, que incluyen sesión activa, agenda del

día y métricas de progreso, se obtendrán en una única llamada al endpoint de resumen

diario en lugar de tres consultas independientes. Silberschatz et al. (2019) señalan que

la reducción de operaciones de entrada y salida entre capas es uno de los factores con

mayor impacto sobre el rendimiento percibido en aplicaciones cliente-servidor.

4.3.4. Compresión y Configuración del Servidor

El  servidor  de  producción  en  centrojuanpabloii.com  se  configurará  con

compresión Gzip o Brotli para los archivos JavaScript, CSS y HTML generados por el

proceso  de  build  de Angular.  El  build  de  producción  de Angular  activa  por  defecto  la

minificación  y  el  tree-shaking,  eliminando  el  código  no  utilizado  del  bundle  final.  Las

33

cabeceras  de  caché  HTTP  se  configurarán  con  tiempos  de  expiración  diferenciados:

largos  para  los  archivos  de  bundle  con  hash  en  el  nombre,  cortos  para  el  archivo

index.html que controla la versión activa de la aplicación.

5. Acuerdos de Niveles de Servicio (SLA) (DIEGO)

5.1. Definición de Indicadores: KPIs operativos del sistema

El  dashboard  de  EduSync  AI  expone  seis  indicadores  que  cubren  el  ciclo

completo de una sesión: desde si se cumplió lo planificado hasta si el docente necesita

ajustar  su  metodología.  Cada  uno  tiene  umbrales  definidos  y  una  fuente  de  datos

concreta en la base de datos del sistema.

5.1.1. Índice de Cobertura del Plan de Sesión

Mide qué porcentaje de los temas y competencias programados en el plan de

sesión  fueron  efectivamente  trabajados  durante  la  clase.  Se  calcula  dividiendo  los

elementos marcados como logrados o parcialmente logrados entre el total de elementos

programados. Un resultado por encima del 90% se considera excelente; entre 70% y

90% es aceptable; por debajo del 70% activa una alerta para el director. La fuente son

los  registros  de  la  tabla  appointments  cruzados  con  session_notes,  donde  queda  el

detalle de qué se cubrió en cada sesión.

5.1.2. Tiempo de Intervención Docente vs. Participación del Alumno

Compara  cuánto  tiempo  habla  el  docente  frente  a  cuánto  tiempo  participa

activamente el alumno. El umbral pedagógico óptimo es que el alumno ocupe entre el

60%  y  el  70%  del  tiempo  de  sesión.  Cuando  el  docente  concentra  más  del  60%  del

tiempo,  la  sesión  se  cataloga  como  expositiva  y  de  baja  calidad  metodológica.  Este

indicador se deriva del análisis de transcripción que realiza el modelo de lenguaje, que

identifica quién habla en cada segmento del audio.

5.1.3. Densidad de Conceptos Clave por Sesión

Cuenta cuántos términos propios del área curricular aparecen en la transcripción

y los relaciona con el total de palabras de la sesión. El umbral varía por materia: Ciencias

exige  más  del  18%,  Matemática  más  del  15%  y  Lenguaje  más  del  12%.  Valores  por

debajo de esos rangos señalan sesiones con poco contenido pedagógico concreto. La

fuente es la transcripción completa cruzada con un diccionario de palabras clave por

área curricular.

5.1.4. Tasa de Precisión de la IA

Registra  qué  porcentaje  de  los  resúmenes  generados  automáticamente  no

fueron editados por el docente después de la sesión. Sobre el 85% indica que el modelo

34

está  funcionando  bien  para  el  contexto  curricular  del  colegio;  entre  70%  y  85%  es

aceptable; por debajo del 70% es una señal de que el modelo necesita ajuste. Este dato

se  almacena  como  un  campo  booleano  en  la  tabla  appointments  que  marca  si  el

resumen fue modificado o no.

5.1.5. Tasa de Cumplimiento de Sesiones Programadas

Divide  las  sesiones  completadas  entre  el  total  de  sesiones  que  estaban

agendadas  en  el  trimestre.  Por  encima  del  95%  es  excelente;  entre  85%  y  95%  es

aceptable;  por  debajo  del  85%  indica  un  problema  de  ausentismo  o  de  continuidad

pedagógica  que  requiere  atención  del  director.  Los  estados  de  cada  sesión  —

programada, completada, cancelada— están registrados en la tabla appointments.

5.1.6. Índice de Satisfacción de Sesión

Promedio de las puntuaciones que alumnos o padres asignan a cada sesión en

una escala del 1 al 10 a través del módulo de retroalimentación. Un promedio entre 8 y

10  es  excelente;  entre  6  y  8  es  aceptable;  por  debajo  de  6  requiere  revisión.  Este

indicador depende de una tabla de feedback asociada a cada cita, lo que lo convierte

en el único KPI cuya activación requiere que los usuarios completen el formulario post-

sesión.

5.2 SLAs del Proyecto: Tiempos de respuesta y disponibilidad prometida.

EduSync AI define sus acuerdos de nivel de servicio en función de la criticidad

de  cada  componente.  No  todos  los  elementos  del  sistema  tienen  el  mismo  peso

operativo, y eso se refleja en los umbrales comprometidos.

5.2.1. Disponibilidad del Sistema

La API REST de Flask es el componente más crítico porque toda operación en

tiempo real depende de ella: se compromete un uptime del 99.5%, lo que equivale a una

tolerancia máxima de 3.6 horas de inactividad al mes. La base de datos PostgreSQL

exige un estándar ligeramente más alto —99.7%, es decir, no más de 2.2 horas de caída

mensual— dado que almacena datos sensibles de sesiones terapéuticas cuya pérdida

o interrupción tiene consecuencias directas sobre la operación. El frontend en Angular,

al ser contenido estático servido desde cPanel, puede comprometer un 99.9% con solo

40 minutos de tolerancia mensual. El servicio de notificaciones opera con un SLA más

holgado del 98% porque su caída no interrumpe las sesiones; y el servicio de correo, al

depender de un servidor SMTP externo, se maneja con un 95% sin garantía propia.

35

 5.2.2. Tiempos de Respuesta por Endpoint

Los endpoints se clasifican en tres grupos según su impacto en la operación.

Los endpoints de sesiones son los más exigentes. Recuperar o actualizar una

sesión debe resolverse en menos de 200ms en el percentil 95 y menos de 400ms en el

percentil  99.  Crear  una  sesión  tiene  un  margen  ligeramente  mayor:  250ms  en  P95  y

500ms en P99. Listar las sesiones de un terapeuta para el calendario puede tardar hasta

300ms en P95 y 600ms en P99. En todos estos casos el límite de error aceptable es

inferior al 0.1%.

Los  endpoints  de  notificaciones  tienen  márgenes  más  amplios  porque  no

bloquean el flujo principal. Crear o listar notificaciones puede tomar hasta 400-800ms

en P99 con un límite de error del 1%. Marcar una notificación como leída debe resolverse

en menos de 200ms.

Los  endpoints  de  validación  son  los  más  ligeros  del  sistema.  Verificar

disponibilidad o validar conflictos de horario debe completarse en menos de 50-100ms

en P95, dado que estas operaciones se ejecutan antes de confirmar cualquier reserva

y el usuario espera respuesta inmediata.

5.2.3. Tiempos por Operación Crítica

La creación de una sesión implica cuatro pasos en secuencia: validar al paciente

(≤20ms), crear el registro en la tabla appointments (≤30ms), asignar los juegos de la

sesión (≤50ms) y hacer commit a la base de datos (≤100ms). El envío de notificaciones

se ejecuta de forma asíncrona y no suma al tiempo de respuesta del usuario. El total

comprometido es 250ms en P95 y 500ms en P99.

La validación de conflictos de horario ejecuta dos verificaciones en paralelo —

que el terapeuta no tenga otra sesión activa y que el paciente tampoco— con un techo

de 50ms cada una, lo que deja el total en 100ms P95 y 200ms P99. Para que ese umbral

sea alcanzable, la base de datos debe tener índices sobre therapist_id, patient_id, status

y el rango de start_time/end_time; sin esos índices el SLA no es sostenible bajo carga.

El  cambio  de  estado  de  una  sesión  —de  "en  progreso"  a  "completada",  por

ejemplo—  es  la  operación  más  rápida  del  sistema:  validación  de  la  transición  más

actualización y commit suman menos de 90ms, con un SLA de 150ms en P95 y 300ms

en P99.

5.2.4. SLAs de Reportes

El dashboard del director con los KPIs en tiempo real debe cargar en menos de

2  segundos  con  datos  actualizados  cada  5  minutos.  Los  reportes  de  sesiones

completadas y asistencia, que se generan con frecuencia diaria, tienen un techo de 3 a

36

5  segundos.  El  análisis  de  cumplimiento  trimestral,  al  ser  el  reporte  más  pesado  en

volumen de datos, puede tomar hasta 10 segundos.

5.2.5. Recuperación ante Fallos

Si PostgreSQL cae, el tiempo objetivo de recuperación es 5 minutos con un punto

de recuperación de 1 minuto, usando el failover disponible en cPanel. Una caída de la

API Flask tiene un RTO de 2 minutos con pérdida cero de datos, porque el proceso se

reinicia automáticamente sin afectar la base de datos. La pérdida de conectividad de red

tolera hasta 10 minutos de recuperación con 5 minutos de datos en riesgo, gestionado

mediante  una  cola  de  reintentos.  En  el  escenario  más  grave  —pérdida  de  datos  que

requiere restaurar desde backup— el RTO es de 30 minutos con un RPO de 24 horas,

que corresponde a la frecuencia del backup diario configurado en el servidor.

5.2.6. Escalamiento ante Violaciones

Cuando  el  sistema  detecta  una  caída  de  más  de  una  hora,  se  genera  una

notificación inmediata al Tech Lead y al Director. Si el P99 supera los 1000ms durante

10 minutos consecutivos, se activan alertas al equipo. Valores de P95 por encima de

500ms  sostenidos  durante  30  minutos  se  registran  y  analizan  automáticamente.  Los

retrasos en notificaciones, al no ser críticos, se revisan en el standup diario sin activar

alerta inmediata.

6. Gestión de Riesgos (DIEGO)

6.1. Matriz de Riesgos: Riesgos del proyecto (retrasos) y riesgos técnicos
(caídas de servidor, pérdida de datos).

ID

Categoría  Descripción del Riesgo

Nivel

Plan de Acción

R01  Despliegue

Incompatibilidad de

Alto

Usar contenedores Docker para

versión entre el entorno

estandarizar el entorno desde

local y el servidor en la

la semana 3 del desarrollo.

nube (riesgo “en mi

máquina sí funciona”).

R02  Despliegue  La ejecución del modelo

Alto

Implementar LLaMA mediante

LLaMA agota la

APIs de inferencia gratuitas o

RAM/CPU del servidor

versiones cuantizadas.

gratuito (Railway/Render)

Establecer límites de peso para

o los audios exceden la

los audios y alertas en AWS.

capa gratuita de AWS S3.

R03  Desarrollo  OpenAI Whisper no

Medio

Aplicar capa de

alcanza el 85% de

preprocesamiento de reducción

37

precisión mínima (RNF05)

de ruido antes de enviar el

por el ruido ambiental

incontrolable del aula

escolar.

audio a Whisper. Realizar

pruebas de campo en semana

4.

R04  Operación

El micrófono lavalier falla

Medio

Protocolo obligatorio pre-clase

(batería o desconexión)

para verificar batería. Como

durante la sesión,

contingencia, habilitar

perdiendo todo el insumo

grabación con el micrófono de

de auditoría.

la laptop desde la app web.

R05  Desarrollo

El modelo LLaMA alucina

Medio

Diseñar System Prompts

al comparar textos o

interpreta mal los

restrictivos que obliguen al

modelo a basarse únicamente

momentos de clase al no

en la transcripción. Implementar

tener restricciones de

módulo de Feedback desde la

tiempo fijo.

primera versión.

R06  Otros

Riesgo legal por vulnerar

Bajo

Configurar eliminación

la privacidad al almacenar

automática e irreversible del

audios con voces de

archivo de audio en AWS S3

menores de edad en la

inmediatamente después de

nube.

que Whisper genere la

transcripción.

R07  Otros

Resistencia o boicot de

Alto

Capacitar a los docentes

docentes al sentirse

enfatizando que EduSync AI es

vigilados por el micrófono

un espejo profesional de su

lavalier y auditados por la

práctica, no una herramienta

IA.

punitiva. Reforzar este mensaje

en la UI.

R08  Operación

El docente olvida iniciar la

Medio

Configurar notificaciones push

grabación al comenzar la

automáticas disparadas 5

clase, perdiendo la

minutos antes de cada sesión

evidencia completa de

desde el módulo de Horarios y

esa sesión.

Aulas.

38

6.2. Plan de Mitigación: Acciones preventivas y correctivas.

6.2.1.  R01 — Incompatibilidad de entornos

El problema clásico de "en mi máquina sí funciona" se resuelve estandarizando

el entorno desde el inicio. El equipo trabaja con un Dockerfile que fija las versiones de

Python,  Flask  y  PostgreSQL,  y  un  docker-compose.yml  que  replica  la  misma

configuración  en  desarrollo,  staging  y  producción.  El  archivo  requirements.txt  y  el

package.json  del  frontend  deben  tener  versiones  explícitas,  sin  rangos.  Antes  de

cualquier  merge  a  la  rama  principal,  GitHub  Actions  ejecuta  el  build  y  las  pruebas

automáticamente. Si el pipeline falla, el merge se bloquea.

6.2.2.  R02 — Saturación de recursos por LLaMA y almacenamiento de audios

El backend define límites estrictos: tamaño máximo de audio de 50MB, timeout

de  LLaMA  en  60  segundos  y  no  más  de  dos  procesos  paralelos  de  inferencia.  El

procesamiento de LLaMA se saca del ciclo de request-response mediante una cola de

tareas con Celery y Redis, de modo que una sesión de análisis pesada no bloquea al

resto de usuarios. Para el almacenamiento, las políticas de ciclo de vida de S3 borran

los archivos automáticamente. El sistema monitorea CPU y memoria en tiempo real y

envía alerta al canal del equipo cuando CPU supera el 80% o memoria el 85%.

6.2.3.  R03 — Precisión insuficiente de Whisper

La estrategia tiene dos capas. Antes de enviar el audio a Whisper, un paso de

preprocesamiento aplica reducción de ruido con la librería noisereduce, que filtra el ruido

de  fondo  típico  de  un  aula.  Si  la  transcripción  resultante  tiene  un  score  de  confianza

menor al 80%, el sistema la rechaza y activa un flujo alternativo donde el docente puede

completar  el  registro  manualmente. A  mediano  plazo,  el  modelo  se  afina  con  audios

reales  grabados  en  colegios  peruanos  para  adaptar  el  vocabulario  y  las  condiciones

acústicas locales. Las pruebas de precisión se corren mensualmente con una muestra

de audios nuevos.

6.2.4.  R04 — Fallo del micrófono lavalier

En cuanto el nivel de carga de la batería baja del 20 %, la aplicación muestra

una alerta visual. Si el micrófono no está activo, el software bloquea el inicio de sesión,

lo que obliga a realizar una verificación antes de que comience la clase. El dispositivo

intenta reconectarse cada 10 segundos si se pierde la conexión durante la grabación.

Además, guarda el audio en una caché interna para poder recuperarlo al reconectarse.

Se deben tener al menos un par de micrófonos de repuesto.

39

6.2.5.  R05 — Interpretación incorrecta de momentos de clase por LLaMA

El sistema no muestra la transcripción completa de una sola vez. En cambio, la

divide en secciones de cinco minutos y muestra cada una por separado con una marca

de tiempo distinta. Esto reduce la probabilidad de que el modelo olvide cuándo ocurrió

cada  evento.  El  director  puede  revisar  los  resúmenes  generados  al  realizar  cambios

antes de guardarlos. Estos ajustes se guardan para poder utilizarlos en futuras mejoras

del  modelo.  El  rendimiento  se  verifica  cada  tres  o  cuatro  meses  con  50  sesiones  de

entrenamiento reales.

6.2.6.  R06 — Privacidad de audios con voces de menores

Una vez que Whisper produce la transcripción, el audio no está más guardado.

La supresión es permanente: el archivo está borrado tres veces antes de ser eliminado,

conforme  a  la  norma  DoD  5220.22-M,  y  cada  eliminación  se  indica  en  el  registro

auditado con una horodatage. Todas las transmisiones de données se escriben a través

de TLS 1.3. Le système est conforme à la loi péruvienne concernant la Protection des

données  personalles  (loi  29733),  y  una  auditoría  legal  se  realiza  cada  período  para

asegurar esta conformidad.

7. Retrospectiva Sprint 2 y Evidencias (DIEGO)

7.1. Análisis de Iteración: Cumplimiento de las Semanas Previas

El Sprint 2 tuvo una duración de una semana y concentró el trabajo del equipo

en construir las interfaces principales de EduSync AI sobre Angular con Tailwind CSS,

organizadas en torno a los tres roles del sistema: director, terapista y paciente. De las

nueve  tareas  planificadas,  cuatro  quedaron  completadas,  tres  en  progreso  y  dos

pendientes. Asimismo, la tasa de cumplimiento se situó en 82% sobre los Story Points

del  ciclo.  Las  tareas  incompletas  no  respondieron  a  problemas  técnicos  sino  a  la

decisión de enfocar el sprint exclusivamente en la capa visual, dejando la integración

con FastAPI para el Sprint 3. El modelo de base de datos también se cerró durante este

período, quedando listo para su implementación en el siguiente ciclo.

Tabla 1 de iteración:

Métrica

Valor

Estado

Story Points Planificados

34

Cerrado

Story Points Completados  28

Parcial

Tasa de Cumplimiento

82%  Aceptable

Bugs Encontrados

2

Controlado

Deuda Técnica Acumulada  6 SP  Moderada

40

Tabla 2 de iteración

Tarea

Responsable

Avance

Bloqueador

T01: Angular + Tailwind CSS  Diego Centeno  100%

T02:  Login  con  redirección

Oscar Prieto

100%

Ninguno

Ninguno

por rol

T03:

Layout

base

y

Diego Centeno  100%

Ninguno

navegación

T09:  Modelo  de  base  de

Diego Centeno  100%

Ninguno

datos

T04:  Dashboard  Director

Diego Centeno  En

Specs sin definir

(KPIs)

progreso

T05: Dashboard Terapista

Oscar Prieto

En

Datos

mock

progreso

insuficientes

T06: Gestión de Pacientes

Benjamín

En

Backend

no

T07: Gestión de Docentes

Benjamín

Pendiente

Trasladado a Sprint 3

Peña

progreso

disponible

T08: Módulo de Horarios

Oscar Prieto

Pendiente

Trasladado a Sprint 3

Peña

La semana arrancó con el setup del proyecto Angular y los componentes base,

que quedaron listos en los primeros dos días y permitieron al equipo trabajar en paralelo

sin esperar dependencias de configuración. Las cuatro tareas completadas sientan la

base  técnica  y  estructural  del  sistema.  Las  tres  en  progreso  tienen  su  capa  visual

terminada y funcionan con datos estáticos, a la espera de los endpoints de FastAPI. T07

y T08 se trasladaron al Sprint 3 por decisión del equipo, priorizando la calidad de los

módulos  ya  iniciados.  Se  detectaron  y  corrigieron  dos  bugs  durante  la  semana:  el

sidebar  no  colapsaba  correctamente  en  pantallas  menores  a  1024px,  y  las  clases

dinámicas de Tailwind en el selector de rol del login presentaban un conflicto de purge

en el build de producción. Ambos quedaron resueltos antes del cierre del sprint.

7.2. Evidencias de Trabajo Grupal

T01: Configurar Proyecto Angular + Tailwind CSS

Responsable: Diego Centeno — Completado (01/04 – 02/04) Story Points: 5

SP

Diego inicializó el repositorio con la estructura de módulos de Angular, separando

desde el inicio los dominios de director, terapista y paciente en carpetas independientes

con sus propios componentes y servicios. Tailwind CSS quedó configurado con la paleta

41

de colores del Centro de Terapias Juan Pablo II. Los componentes base Button, Card y

Modal  se  construyeron  como  unidades  reutilizables  que  el  equipo  utilizó  sin

modificaciones  en  las  vistas  posteriores.  El  trabajo  cerró  en  dos  días,  habilitando  a

Oscar y Benjamín para arrancar sus tareas sin esperar configuraciones de entorno.

Evidencias:

•  Repositorio Angular con estructura de módulos por dominio (director, terapista,

paciente)

•  Tailwind CSS configurado con paleta corporativa
•  Componentes base Button, Card y Modal operativos y reutilizables
•  Servicios HTTP base para consumo de API
•  README y gitignore documentados

T02: Desarrollar Pantalla de Login con Redirección por Rol

Responsable: Oscar Prieto — Completado (02/04 – 03/04) Story Points: 5 SP

Se construyó la pantalla de autenticación del sistema con selector de rol para

director,  terapista  y  padre  de  familia.  El  formulario  valida  el  formato  del  correo  y  la

contraseña  antes  de  consultar  el  backend.  Una  vez  autenticado,  el  sistema  lee  el  rol

devuelto  por  la  API  y  redirige  al  usuario  de  forma  automática  a  la  vista  que  le

corresponde.  Si  las  credenciales  son  incorrectas  o  el  servidor  no  responde,  el  error

aparece en pantalla sin recargar la página. Esta tarea responde directamente a HU-02,

que  establece  que  cada  usuario  debe  acceder  exclusivamente  a  las  funciones

habilitadas para su perfil.

Evidencias:

•  Pantalla de login responsive con selector de rol (director, terapista, paciente)
•  Validación de campos en el cliente antes del envío al servidor
•  Almacenamiento de token JWT en localStorage
•  Redirección automática diferenciada por rol
•  Mensajes de error dinámicos sin recarga de página

T03: Construir Layout Base con Navegación por Rol

Responsable: Diego Centeno — Completado (03/04 – 04/04) Story Points: 5

SP

Se armó el esqueleto de navegación adaptado a los tres perfiles del sistema. El

sidebar  muestra  opciones  distintas  según  el  rol  activo  y  se  colapsa  en  resoluciones

menores  a  1024px.  El  header  expone  el  nombre  del  usuario  y  el  botón  de  cierre  de

sesión. Durante las pruebas se detectó que el sidebar no colapsaba correctamente en

pantallas pequeñas por un error en el manejo de estado del componente de layout, que

42

se

resolvió  usando  el  hook  correspondiente  con  breakpoint  detectado  por

ResizeObserver. También se corrigió el conflicto de purge en Tailwind que impedía que

las clases del selector de rol se aplicaran correctamente en producción.

Evidencias:

•  Sidebar colapsable con navegación filtrada por rol
•  Header responsive con nombre de usuario y logout
•  Rutas protegidas configuradas en Angular Router
•  Bug de colapso en resoluciones menores a 1024px corregido
•  Conflicto de purge en clases dinámicas de Tailwind resuelto

T04: Implementar Dashboard Director (KPIs)

Responsable: Diego Centeno — En progreso (04/04 – 08/04) Story Points: En

progreso

El  dashboard  del  director  consolida  en  una  sola  pantalla  el  índice  de

cumplimiento global del centro, las sesiones activas del día y las alertas de terapistas

con  desviación  significativa  respecto  a  su  plan.  Diego  completó  toda  la  capa  visual:

tarjetas de indicadores, tabla de estado de auditoría por terapista y gráfico de tendencias

con  selector  de  período.  La  vista  opera  con  datos  estáticos  de  prueba.  El  avance  se

detuvo al requerir definición precisa de qué métricas debe calcular el backend para cada

tarjeta, aspecto pendiente de resolución al inicio del Sprint 3 junto con la conexión al

endpoint de FastAPI.

Evidencias:

•  Tarjetas de KPIs con índice de cumplimiento, sesiones activas y alertas críticas
•  Tabla de auditoría por terapista con estado de cumplimiento
•  Gráfico de tendencias con selector de período (semanal)
•  Animaciones y transiciones visuales completadas
•  Conexión al endpoint de KPIs pendiente para Sprint 3

T05: Implementar Vista Dashboard del Terapista

Responsable: Oscar Prieto — En progreso (04/04 – 08/04) Story Points: En

progreso

Se  construyó  la  vista  que  centraliza  la  jornada  del  terapista.  Un  encabezado

dinámico indica la próxima sesión del día con nombre del paciente y hora. El módulo

central muestra la sesión activa con porcentaje de cobertura del plan terapéutico, meta

semanal y desglose de temas según su estado: logrado, parcial o pendiente. La agenda

del día completa aparece en una columna lateral en formato cronológico. Todo opera

43

con  datos  estáticos.  La  conexión  con  el  endpoint  de  sesiones  de  FastAPI  queda

pendiente para el Sprint 3.

Evidencias:

•  Encabezado dinámico con próxima sesión del día y datos del paciente
•  Barra de cobertura del plan con porcentaje y meta semanal
•  Desglose de temas por estado: logrado, parcial, pendiente
•  Agenda diaria completa en columna lateral
•

Integración con endpoint de sesiones pendiente

T06: Desarrollar Módulo Gestión de Pacientes

Responsable: Benjamín Peña — En progreso (02/04 – 08/04) Story Points: En

progreso

Benjamín  construyó  el  módulo  de  gestión  de  pacientes  con  tabla  paginada,

búsqueda por nombre o DNI y filtros por grado y sección. Cada fila muestra identificador,

nombre  completo,  contacto  del  apoderado  y  estado  de  pago  con  etiqueta  de  color

diferenciada.  El  modal  de  registro  valida  los  campos  obligatorios  antes  de  enviar  los

datos. La vista está completa con datos de prueba. La integración con el endpoint de

pacientes de FastAPI, que cubriría las operaciones CRUD completas, quedó pendiente

por no estar disponible el backend durante el período del sprint.

Evidencias:

•  Tabla paginada con búsqueda por nombre y número de documento
•  Filtros por grado y sección operativos
•  Modal de registro con validación de campos obligatorios
•  Etiquetas de estado de pago diferenciadas por color
•  Bloque de resumen con total de pacientes matriculados
•

Integración con API de pacientes pendiente para Sprint 3

T07: Diseñar Modelo de Base de Datos

Responsable: Diego Centeno — Completado (01/04 – 03/04) Story Points: 5

SP

Se  diseñó  y  documentó  el  modelo  de  datos  con  12  tablas  relacionadas  que

cubren  el  módulo  administrativo  del  centro  y  el  motor  de  auditoría  IA.  Las  tablas

principales  vinculan  usuarios,  pacientes,  terapistas,  sesiones,  planes  de  sesión,

transcripciones, reportes de auditoría, asistencia, comunicados y pagos mediante claves

foráneas  que  garantizan  la  integridad  referencial.  Cada  sesión  queda  vinculada  a  su

plan de origen, cada transcripción a su sesión y cada reporte a la transcripción que lo

generó, lo que permite rastrear el ciclo completo de una atención desde la planificación

hasta  la  auditoría.  Este  modelo  queda  listo  para  su  implementación  en  PostgreSQL

durante el Sprint 3.

44

Evidencias:

•  12 tablas diseñadas con campos, tipos de dato y relaciones definidas
•  Claves foráneas que garantizan integridad referencial entre entidades
•  Cobertura del módulo ERP y del motor de auditoría IA
•  Modelo documentado y validado para implementación en PostgreSQL

Tabla Resumen de Evidencias

Tarea

Responsable

Estado

SP  Bloqueador

T01: Angular + Tailwind

Diego Centeno  100%

T02: Login por rol

Oscar Prieto

100%

T03: Layout base

Diego Centeno  100%

T09: Modelo de datos

Diego Centeno  100%

5

5

5

5

Ninguno

Ninguno

Ninguno

Ninguno

T04: Dashboard Director  Diego Centeno  En progreso  —

Specs KPIs

T05: Dashboard Terapista  Oscar Prieto

En progreso  —

Backend

T06: Gestión Pacientes

Benjamín Peña  En progreso  —

Backend

T07: Gestión Docentes

Benjamín Peña  Pendiente  —

Sprint 3

T08: Módulo Horarios

Oscar Prieto

Pendiente  —

Sprint 3

Total

—

82%

28/34  3 activos

Completadas

•  Stack Angular con Tailwind CSS configurado y operativo
•  Autenticación con selector de rol y redirección automática diferenciada
•  Layout de navegación con sidebar colapsable y header responsive
•  Modelo de base de datos con 12 tablas documentadas y listo para

PostgreSQL

•  Vistas de Dashboard del director, Dashboard del Terapista y Gestión de

Pacientes funcionales con datos estáticos

•  Dos bugs detectados y corregidos durante la semana

Pendientes para Sprint 3

•  Conectar Dashboard del director con endpoint de KPIs de FastAPI
•  Conectar Dashboard del Terapista con endpoint de sesiones activas
•  Completar integración de Gestión de Pacientes con operaciones CRUD
•  Desarrollar módulo de Gestión de Docentes (T07)
•  Construir módulo de Horarios y Aulas (T08)
•  Establecer conexión con base de datos PostgreSQL

Retrospectiva del Equipo

En primer lugar, lo que salió bien fue definir los componentes base el primer día

de  la  semana  fue  determinante:  ningún  integrante  tuvo  que  detenerse  a  resolver

45

problemas  de  configuración  mientras  desarrollaba  sus  vistas. También,  el  modelo  de

base de datos cerrado en los primeros días también permitió que el equipo diseñara los

componentes  sabiendo  exactamente  qué  estructura  de  datos  recibirían  del  backend.

Los dos bugs detectados y corregidos durante la misma semana evitaron que llegaran

al Sprint 3 como deuda acumulada.

En contrario, el T04 perdió tiempo esperando que se definieran los indicadores

exactos  del  dashboard  del  director,  dependencia  que  no  estaba  registrada  en  la

planificación y no se detectó hasta que el desarrollo ya estaba en curso. Aquí mismo, se

ve  la  ausencia  total  de  backend  durante  el  sprint  limitó  las  pruebas  a  navegación,

renderizado  y  validación  de  formularios,  sin  poder  verificar  que  los  componentes

consumen y muestran datos reales de forma correcta.

Por último, de compromiso para el Sprint 3, el equipo acordó levantar FastAPI

desde el primer día del siguiente ciclo para no repetir el problema de pruebas solo con

datos estáticos, documentar el contrato de cada endpoint en Swagger antes de iniciar

cualquier integración, y establecer las pruebas con Jasmine desde el primer commit de

cada tarea nueva.

46

Bibliografía

Web Vitals. (n.d.). Web.Dev. https://web.dev/articles/vitals?hl=es-419

Usability Engineering. Jakob Nielsen. (1994). Nielsen Norman Group.

https://www.nngroup.com/books/usability-engineering/

Silberschatz, A., Korth, H. F., & Sudarshan, S. (2019). Database system concepts (7th

ed.). McGraw-Hill Education.

47

