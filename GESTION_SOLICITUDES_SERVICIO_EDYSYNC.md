# GESTIÓN DE SOLICITUDES DE SERVICIO: Herramientas, Mejores Prácticas y Procedimiento de Acceso al Sistema

**UNIVERSIDAD TECNOLÓGICA DEL PERÚ | Curso Integrador II: Sistemas**

*Informe de Práctica Aplicada — Semana 10, Sesión 2 | Piura, 2025*

---

## 1. Introducción

El presente informe ha sido elaborado en el marco de la Semana 10, Sesión 2 del curso Integrador II: Sistemas de la Universidad Tecnológica del Perú (UTP). Su propósito es dar cumplimiento al Logro de Aprendizaje establecido para la sesión y desarrollar la actividad práctica propuesta en la Fase 5.

Según el logro de aprendizaje definido, al finalizar la sesión el estudiante debe ser capaz de *"diseñar estrategias de atención, evidenciando su aprendizaje mediante la creación de un procedimiento y formato de solicitud, alineado estrictamente a las necesidades de su proyecto integrador"*.

Para lograr este objetivo, el presente documento aborda, en primer lugar, el marco teórico sobre gestión de solicitudes de servicio de TI y sus mejores prácticas conforme al estándar ITIL 4, y en segundo lugar, desarrolla un caso práctico completo: el diseño de un procedimiento y formato de solicitud de acceso a módulos críticos del sistema EduSync AI — la plataforma digital del Centro de Terapias Juan Pablo II.

---

## 2. Marco Teórico: Gestión de Solicitudes de Servicio de TI

### 2.1. El Problema del Caos Manual

Cuando una organización despliega un sistema de información a escala, comienza a recibir un volumen creciente de solicitudes de soporte por parte de los usuarios finales. Sin una plataforma estructurada de gestión, estas peticiones llegan de forma desordenada a través de correos electrónicos, llamadas telefónicas o mensajes informales con asuntos vagos como *"no entra"* o *"olvidé mi contraseña"*.

En el contexto específico del Centro de Terapias Juan Pablo II, antes de la implementación de EduSync AI, la gestión de accesos y cambios en el sistema era completamente manual:
- Los terapeutas enviaban correos no formales solicitando acceso a nuevas funciones o módulos
- La administradora anotaba estos pedidos en un cuaderno y los gestionaba sin criterios de seguridad definidos
- No existía un registro de auditoría de quién había solicitado qué permiso y cuándo fue aprobado
- Las solicitudes relacionadas con información sensible (reportes financieros, datos de pacientes) no pasaban por validaciones de seguridad

**Impacto del Caos Manual:**

- **60%** del tiempo de los ingenieros/administradores se pierde clasificando correos mal redactados en lugar de aportar valor real al negocio
- Cada minuto que un usuario espera por un acceso representa un minuto de productividad perdida para la institución (ej. un terapeuta no puede ver el progreso de su paciente si no tiene acceso al módulo de métricas)
- Sin herramientas de gestión adecuadas, los equipos de TI se limitan a apagar incendios en lugar de construir servicios de valor *(Principio de Operación de Servicios – ITIL 4)*
- **Mayor riesgo de seguridad:** accesos otorgados sin validación formal constituyen un fallo crítico de control interno, especialmente en sistemas que manejan datos sensibles como información clínica y financiera de menores de edad

### 2.2. Tipos de Solicitudes de Servicio

Las peticiones de servicio se clasifican en dos grandes grupos:

| SOLICITUDES DE INFORMACIÓN | SOLICITUDES DE ACCESO |
| :--- | :--- |
| El usuario tiene dudas sobre cómo usar el sistema, necesita manuales, guías, o quiere conocer el estado de un trámite | El usuario requiere permisos formales para interactuar con sistemas, módulos o bases de datos confidenciales |
| **Objetivo:** Responder rápido y de preferencia de forma automática mediante una base de conocimiento | **Objetivo:** Validar la seguridad y obtener aprobaciones antes de actuar; mantener un registro de auditoría permanente |
| **Ejemplo en EduSync AI:** "¿Cómo veo las métricas de progreso de mi paciente?", "¿Cómo descargo un reporte?" | **Ejemplo en EduSync AI:** "Necesito acceso al módulo de reportes financieros", "Solicito permisos para gestionar pagos en el sistema" |

### 2.3. Componentes de una Plataforma de Gestión de Servicios de TI

Una plataforma de gestión de servicios de TI profesional se articula sobre seis componentes clave, divididos en dos grupos: pilares de interacción con el usuario y motor lógico interno.

#### 2.3.1. Pilares de la Plataforma (Interacción con el Usuario)

- **COMPONENTE 1: Portal Único de Usuario**
  
  Es la ventanilla única donde el usuario final ingresa para pedir ayuda, sin necesidad de saber quién lo atenderá internamente. Reemplaza definitivamente al correo electrónico o al teléfono como medio principal de contacto.
  
  En el contexto de EduSync AI, el Portal Único se materializa a través de:
  - Un módulo de **Solicitudes y Cambios** integrado en el dashboard del usuario (terapeutas, administradores)
  - Un formulario estructurado accesible desde el menú principal del sistema
  - Un registro de todas las solicitudes históricas del usuario en un apartado "Mis Solicitudes"
  
  **Ventajas clave:** Centraliza todas las peticiones en un solo lugar; permite al usuario ver el estado exacto de su trámite en tiempo real; brinda una apariencia profesional y unificada al departamento de TI; genera un historial auditable de todas las transacciones.

- **COMPONENTE 2: Catálogo de Servicios**
  
  Es la lista detallada y estandarizada de todo lo que los usuarios pueden solicitar. Funciona como un menú estructurado (tipo tienda virtual) que agrupa todo lo que TI puede ofrecer de forma ordenada.
  
  En lugar de recibir mensajes genéricos, el usuario selecciona del catálogo una opción clara. Por ejemplo:
  - *Accesos > Módulo de Métricas y Reportes > Solicitar acceso a reportes de progreso*
  - *Accesos > Módulo Administrativo > Solicitar permisos de gestión de pagos*
  - *Cambios > Importar Datos > Solicitar importación de pacientes desde Excel*
  
  *Principio de diseño:* El catálogo debe estar diseñado para la persona que tiene el problema, no para quien lo repara. Usar lenguaje del usuario, no jerga técnica.
  
  En EduSync AI, el catálogo de servicios se organiza en **Categorías** que reflejan las funciones del sistema:
  - **Accesos y Permisos:** Solicitudes relacionadas con roles, módulos y funcionalidades
  - **Datos y Reportes:** Solicitudes de exportación, análisis customizado o cambios de estructura de datos
  - **Configuración:** Cambios en parámetros del sistema, definiciones de planes de pago, sedes, etc.
  - **Soporte Técnico:** Errores, lentitud, falta de sincronización

- **COMPONENTE 3: Base de Conocimiento**
  
  Repositorio estructurado de artículos, manuales y respuestas frecuentes que permite a los usuarios resolver sus dudas por sí mismos.
  
  Las plataformas modernas muestran artículos sugeridos mientras el usuario escribe su petición. Si el artículo resuelve el problema, el usuario cierra la pantalla y la petición nunca llega a los ingenieros. A esto se le conoce como *desvío de peticiones* y es una de las métricas más críticas de eficiencia en ITIL.
  
  Para EduSync AI, la Base de Conocimiento incluye:
  - Guías paso a paso: "Cómo crear una sesión", "Cómo registrar un pago", "Cómo ver métricas"
  - Preguntas frecuentes: "¿Por qué mi contraseña no funciona?", "¿Cómo cambio mi sede asignada?"
  - Troubleshooting: "Mi paciente no puede acceder a los juegos", "No me deja exportar un reporte"
  - Políticas y procedimientos: "Qué es el ANS de acceso", "Cuándo debo solicitar un permiso"

#### 2.3.2. Motor de la Plataforma (Lógica Interna)

| Componente | Descripción y función |
| :--- | :--- |
| **Flujos de Trabajo (Workflows)** | Orquestan paso a paso qué debe ocurrir. Ejemplo: Si se solicita acceso al módulo financiero, primero pasa por aprobación del jefe inmediato (terapeuta responsable), luego a validación del Gerente, luego a implementación técnica. Eliminan el seguimiento manual |
| **Reglas de Asignación** | Envían automáticamente la petición al grupo resolutor correcto (ej. Equipo de Sistemas, Gerencia, Oficial de Seguridad) evitando el trabajo manual de un coordinador humano. Se basan en metadatos de la solicitud como el tipo de acceso, la sensibilidad de la información y el perfil del solicitante |
| **Acuerdos de Nivel de Servicio (ANS)** | Cronómetros invisibles que miden el tiempo desde que entra la petición hasta que se resuelve, disparando alertas si se demora. Incluyen tiempo de respuesta (cuándo respondemos confirmando la recepción) y tiempo de resolución (cuándo solucionamos la petición) |

### 2.4. Acuerdos de Nivel de Servicio (ANS) en el Contexto de EduSync AI

Los ANS son compromisos documentados entre el proveedor de TI y el negocio, donde se establecen tiempos máximos de atención. Son fundamentales para la transparencia y la confianza organizacional.

**Elementos Clave de un ANS:**

- **Pacto Formal:** Compromiso documentado con tiempos máximos de atención
- **Tiempo de Respuesta vs. Resolución:** El primero mide cuánto tardamos en decir *"Estamos trabajando en ello"* y usualmente está entre 4 y 8 horas hábiles; el segundo mide cuándo solucionamos la petición (entre 24 y 72 horas dependiendo de la complejidad)
- **Alertas Tempranas:** Las plataformas configuran alarmas (ej. al **75%** del tiempo consumido) para evitar el incumplimiento del acuerdo

**ANS Propuestos para EduSync AI:**

| Tipo de Solicitud | Prioridad | Tiempo de Respuesta | Tiempo de Resolución | Justificación |
| :--- | :--- | :--- | :--- | :--- |
| Solicitud de acceso a módulo de lectura (Métricas, Reportes) | Media | 4 horas hábiles | 24 horas hábiles | No impacta operación inmediata; requiere validación de datos |
| Solicitud de acceso a módulo administrativo (Pagos, Citas) | Alta | 2 horas hábiles | 8 horas hábiles | Crítica para operación diaria; requiere validación y entrenamiento |
| Solicitud de acceso a datos financieros o información clínica sensible | Crítica | 1 hora hábil | 4 horas hábiles | Requiere múltiples aprobaciones y auditoría de seguridad |
| Reporte de error técnico ("No puedo ingresar", "Sistema lento") | Alta | 1 hora hábil | 4 horas hábiles | Impacta productividad del usuario |
| Solicitud de información general (Base de Conocimiento) | Baja | Automática | 2 horas hábiles | Puede resolverse mediante artículos de KB; si no, escala |

### 2.5. Mejores Prácticas Universales

**2.5.1. Resolución Anticipada y Desvío de Peticiones**

La mejor petición es la que nunca llega a requerir atención humana. Fomentar la autogestión reduce drásticamente los costos operativos. Si el usuario puede consultar guías o restablecer su propia contraseña de forma segura, el equipo técnico se libera para tareas verdaderamente críticas.

En EduSync AI, esto se materializa mediante:
- Un portal de autorrestablecimiento de contraseñas integrado en la página de login
- Documentación video-tutorial para procesos comunes
- FAQ interactivo con búsqueda por palabras clave
- Notificaciones proactivas (ej. "Acceso denegado porque tu documento de pago está vencido")

**Métrica de Éxito:** Lograr que al menos el **40%** de las solicitudes se resuelvan sin intervención humana mediante la base de conocimiento.

**2.5.2. Lenguaje del Usuario vs. Lenguaje Técnico**

El catálogo debe diseñarse para la persona que tiene el problema, no para quien lo repara:

- **MAL DISEÑO (Técnico):** 
  - "Elevación de privilegios en tabla de usuarios de rol 'admin'"
  - "Sincronización de permisos con caché de sesión distribuida"
  - "Acceso de lectura a vistas materializadas de métricas"
  
- **BUEN DISEÑO (Usuario):**
  - "Solicitar acceso a ver el dashboard administrativo"
  - "Necesito que mi cuenta funcione en todos mis dispositivos"
  - "Quiero ver los reportes de progreso de mis pacientes"

En EduSync AI, hemos diseñado el catálogo de servicios usando terminología del negocio de terapia, no de tecnología:
- "Acceso al Módulo de Pacientes" en lugar de "Query read-only a tabla User con role='jugador'"
- "Registro de una nueva sesión" en lugar de "POST a endpoint /api/appointments con payload serializado"
- "Descarga de reportes de cumplimiento" en lugar de "Exportación a .xlsx desde vistas de base de datos"

**2.5.3. Recopilación de Datos Exactos**

- **Formularios Dinámicos:** Cada servicio del catálogo debe tener un formulario específico. No usar una caja de texto libre para todo. El formulario debe cambiar sus campos según lo que el usuario seleccione (ej. si solicita acceso a módulo financiero, debe aparecer un campo "Centro de costos"; si solicita acceso a módulo de pacientes, debe aparecer un campo "Sede asignada")

- **Campos Obligatorios:** Si pedir un acceso requiere información específica (ej. código de empleado, sede, justificación del negocio), hacerlo un campo obligatorio. Evitará correos de ida y vuelta preguntando datos faltantes.

- **Justificación del Negocio:** Para accesos a sistemas, siempre incluir un campo donde el usuario explique por qué necesita el permiso para sus labores. Esto es crítico para auditoría y para que los aprobadores tomen decisiones informadas.

**Ejemplo de recopilación exacta en EduSync AI:**

Cuando un nuevo terapeuta solicita acceso al módulo de métricas de un paciente, el sistema debe preguntar:
1. ¿A qué pacientes específicos necesitas ver métricas? (lista de pacientes del usuario)
2. ¿Necesitas solo lectura o también exportación de reportes? (opciones)
3. ¿Por qué necesitas este acceso? (texto libre, mín. 10 caracteres)
4. ¿A partir de qué fecha? (selector de fecha)
5. ¿Acceso permanente o temporal? Si es temporal, ¿hasta cuándo? (radio button + fecha condicional)

### 2.6. Anti-patrones: Errores Comunes a Evitar

Los siguientes son errores comunes que degradan la experiencia de usuario y la eficiencia del equipo de TI:

1. **Formularios Interminables:** Pedir 20 datos al usuario para solicitar un cambio de teclado. El usuario se frustrará y llamará por teléfono. En EduSync AI, el objetivo es que ningún formulario exceda 6 campos.

2. **Síndrome de "Todo es Urgente":** Si el sistema permite al usuario elegir la prioridad, el **99%** elegirá "Alta". La prioridad la debe calcular la plataforma según el tipo de servicio, no el usuario. En EduSync AI, la prioridad se determina automáticamente según la categoría de la solicitud y la sensibilidad de los datos.

3. **Respuestas Robóticas:** Cerrar peticiones con mensajes técnicos como *"Error 404 solucionado en server 3"* en lugar de *"Su acceso ha sido verificado y ahora puede ver los reportes desde el menú 'Análisis > Mis Pacientes'"*.

4. **Falta de Trazabilidad:** No registrar quién aprobó, quién implementó y cuándo se implementó cada cambio. Esto es especialmente crítico en sistemas que manejan datos sensibles de menores de edad.

5. **Ausencia de Límites de Tiempo:** Las solicitudes quedan en estado "pendiente" indefinidamente. Esto crea una imagen de desorden y falta de profesionalismo.

> **Regla de Oro en Arquitectura de Servicios:** *"Automatizar un proceso ineficiente solo logrará que las cosas fallen mucho más rápido. Primero se ordena el proceso, luego se implementa la herramienta."* — ITIL 4 Practitioner

---

## 3. Práctica Aplicada: Procedimiento y Formato de Solicitud de Acceso para EduSync AI

De acuerdo con los pasos de la actividad (Fase 5), el equipo de proyecto ha identificado los siguientes casos reales del sistema integrador, ha diseñado los formatos de solicitud y ha definido los flujos de aprobación correspondientes.

### 3.1. Paso 1 — Identificación de Casos de Acceso Críticos

En el contexto de EduSync AI, el Centro de Terapias Juan Pablo II maneja información altamente sensible: datos clínicos de menores de edad, información financiera de las familias, y diagnósticos terapéuticos. Por lo tanto, se han identificado **tres casos críticos** de solicitud de acceso que requieren procedimientos formales y estructurados.

#### **CASO 1: Acceso al Módulo de Reportes y Análisis de Pacientes**

- **Sistema:** EduSync AI — Plataforma de Gestión Integral del Centro de Terapias
- **Módulo involucrado:** Reportes y Análisis de Progreso (métricas, gráficos, exportación de reportes)
- **Tipo de solicitante:** Terapeuta que requiere consultar el progreso de sus pacientes asignados
- **Naturaleza del acceso:** Acceso de solo lectura (consulta de reportes) o acceso con permisos de exportación
- **Motivo de criticidad:** El módulo contiene información clínica sobre el desempeño de los pacientes (puntuaciones, avances en objetivos terapéuticos, recomendaciones). Un acceso otorgado sin validación formal podría permitir que un terapeuta vea información de pacientes que no tiene a su cargo, violando confidencialidad

#### **CASO 2: Acceso al Módulo de Gestión Financiera y Pagos**

- **Sistema:** EduSync AI
- **Módulo involucrado:** Registro de Pagos, Cálculo de Deudas, Gestión de Planes de Pago
- **Tipo de solicitante:** Administrativo, recepcionista o personal autorizado que debe registrar ingresos de dinero
- **Naturaleza del acceso:** Acceso con permisos de edición (registrar pagos, crear/modificar planes)
- **Motivo de criticidad:** El módulo contiene información financiera sensible y transaccional. El acceso sin validación podría resultar en fraude, malversación de fondos, o alteration de registros de pago. Este acceso debe ser auditado exhaustivamente

#### **CASO 3: Acceso al Módulo Administrativo Completo (Super Usuario)**

- **Sistema:** EduSync AI
- **Módulo involucrado:** Gestión de Usuarios, Configuración del Sistema, Importación/Exportación de Datos Masivos
- **Tipo de solicitante:** Gerencia o responsable de TI del centro
- **Naturaleza del acceso:** Acceso completo con permisos de creación, modificación, eliminación y auditoría
- **Motivo de criticidad:** Este nivel de acceso permite alterar la configuración del sistema completo, cambiar roles de usuarios, o exportar datos masivos. Es el nivel más sensible después de credenciales de base de datos

A continuación, se desarrolla en detalle el **CASO 1 (Acceso a Reportes)** como caso práctico completo.

---

### 3.2. Paso 2 — Diseño del Formato de Solicitud de Acceso

A continuación se presenta el formato oficial de solicitud de acceso, diseñado siguiendo las mejores prácticas establecidas: lenguaje del usuario, campos necesarios y suficientes, justificación del negocio obligatoria, y trazabilidad completa de aprobaciones.

#### **FORMATO DE SOLICITUD DE ACCESO A MÓDULOS — EduSync AI**

*Centro de Terapias Juan Pablo II | Departamento de Administración*

*Código del Formato: EDS-ACC-001-v1 | Vigencia: 2025*

---

**SECCIÓN 0: REGISTRO ADMINISTRATIVO**

| Campo | Valor |
| :--- | :--- |
| **N.º de Solicitud:** | EDS-ACC-_______-[Año] |
| **Fecha de Solicitud:** | __/__/______ |
| **Prioridad Calculada:** | [ ] Crítica [ ] Alta [ ] Media [ ] Baja |
| **ANS Aplicable:** | Según tabla ANS v1 (ver sección 2.4) |
| **Sistema Afectado:** | EduSync AI v2.5+ |
| **Módulo Solicitado:** | [ ] Reportes [ ] Financiero [ ] Administrativo [ ] Otro |

---

**SECCIÓN 1: DATOS GENERALES DEL SOLICITANTE**

* **Apellidos y Nombres:** ________________________________________
* **Correo Institucional:** ________________________________________
* **Celular/Teléfono:** ________________________________________
* **Área / Departamento:** [ ] Administración [ ] Terapeutas [ ] Logística [ ] Otro
* **Cargo / Puesto:** ________________________________________
* **Sede de Trabajo:** [ ] Piura [ ] Chiclayo [ ] Otra: _______________
* **Fecha de Ingreso al Centro:** __/__/______
* **¿Tienes experiencia previa con sistemas similares?:** [ ] Sí [ ] No
  * Si respondiste "Sí", describe brevemente: _____________________________________

---

**SECCIÓN 2: TIPO DE SOLICITUD Y ESPECIFICACIÓN DE ACCESO**

**2.1 — Tipo de Operación:**
* [ ] **Acceso Nuevo** (nunca he tenido este módulo)
* [ ] **Ampliación de Acceso** (ya tengo algo, pero necesito más)
* [ ] **Modificación de Acceso Existente** (tengo acceso pero necesito cambios)
* [ ] **Renovación de Acceso** (mi acceso expiró y necesito reactivarlo)
* [ ] **Eliminación de Acceso** (ya no necesito este permiso)

**2.2 — Selecciona el Módulo que Necesitas:**

* [ ] **MÓDULO DE REPORTES Y ANÁLISIS**
  * [ ] Reportes de Progreso de Mis Pacientes (solo lectura)
  * [ ] Reportes de Progreso + Descarga de Archivos (.xlsx)
  * [ ] Reportes de Progreso + Análisis Comparativo
  * [ ] Reportes de Cumplimiento Terapéutico (métricas avanzadas)
  * ¿De cuál(es) paciente(s)? (seleccionar): ______________________________

* [ ] **MÓDULO FINANCIERO**
  * [ ] Ver Deudas y Estado de Cuenta de Mis Pacientes (lectura)
  * [ ] Registrar Pagos (crear nuevos registros de ingresos)
  * [ ] Gestionar Planes de Pago (crear/modificar planes)
  * [ ] Generar Reportes Financieros (análisis de ingresos)
  * ¿Cuál es tu rol en la gestión financiera? ______________________________

* [ ] **MÓDULO ADMINISTRATIVO**
  * [ ] Gestión de Usuarios (crear, modificar, activar/desactivar)
  * [ ] Configuración del Sistema (cambiar parámetros)
  * [ ] Importación de Datos Masivos (carga de usuarios, pacientes)
  * [ ] Auditoría y Logs (ver historial de cambios)
  * Justificación de por qué necesitas acceso administrativo:
  _________________________________________________________________

* [ ] **OTRO (ESPECIFICAR):**
  _________________________________________________________________

---

**SECCIÓN 3: JUSTIFICACIÓN DEL NEGOCIO**

* **Describe brevemente POR QUÉ necesitas este acceso para desempeñar tu trabajo:**
  _________________________________________________________________
  _________________________________________________________________
  _________________________________________________________________

* **¿Cuál es el IMPACTO en tu trabajo si NO tienes este acceso?**
  (ej. "No puedo ver el progreso de mis pacientes", "Pierdo 2 horas diarias en cálculos manuales")
  _________________________________________________________________
  _________________________________________________________________

* **¿Con quién coordinaste esta solicitud?** (nombre del jefe/supervisor):
  ________________________________________________________________

* **Vigencia del acceso solicitado:**
  * [ ] **Permanente** (mientras ocupe este cargo)
  * [ ] **Temporal** — desde __/__/______ hasta __/__/______
  * [ ] **Por Proyecto** — nombre del proyecto: _________________________

* **¿Cuentas con acceso similar en otro sistema o en una sede diferente?**
  * [ ] Sí — especifica: _______________________________________________
  * [ ] No

---

**SECCIÓN 4: DECLARACIÓN DE CUMPLIMIENTO Y CONFIDENCIALIDAD**

Declaro que:

- [ ] He leído y entiendo los términos de confidencialidad del Centro de Terapias
- [ ] Comprendo que accederé a información sensible (datos clínicos de menores de edad, información financiera) y me comprometo a tratarla con máxima confidencialidad
- [ ] Usaré los accesos solamente para los propósitos indicados en esta solicitud
- [ ] Reportaré cualquier acceso indebido o cambio sospechoso en mis permisos
- [ ] Entiendo que el incumplimiento de estos términos puede resultar en la terminación de mi contrato

**Firma del Solicitante:** _________________ **Fecha:** __/__/______

**Huella Digital o RUC (opcional):** _________________________________

---

**SECCIÓN 5: VALIDACIÓN POR EL JEFE INMEDIATO**

* **Jefe/Supervisor que autoriza la solicitud:**
  * Nombre: ________________________________________________________
  * Cargo: _________________________________________________________
  * Correo: ________________________________________________________

* **¿Autoriza el acceso solicitado?**
  * [ ] **Autorizo completamente** — El solicitante necesita exactamente esto
  * [ ] **Autorizo con cambios** — especifica cuáles: _____________________
  * [ ] **No autorizo** — razón: _________________________________________

* **Comentarios adicionales del jefe:**
  _________________________________________________________________
  _________________________________________________________________

**Firma del Jefe:** _________________ **Fecha:** __/__/______

**Responsabilidad de la Aprobación:** El jefe inmediato certifica que:
1. El solicitante está autorizado a acceder a la información solicitada
2. El acceso es necesario para sus funciones actuales
3. La información está siendo solicitada para propósitos legítimos de negocio

---

**SECCIÓN 6: VALIDACIÓN POR EL DUEÑO DE LA INFORMACIÓN (Data Owner)**

El Dueño de la Información es quien responsablemente gestiona el módulo o los datos:
- Para Módulo de Reportes: **Terapeuta Responsable o Gerencia Clínica**
- Para Módulo Financiero: **Administrador General o Contador**
- Para Módulo Administrativo: **Gerente General o Responsable de TI**

* **Dueño de la Información que valida:**
  * Nombre: ________________________________________________________
  * Cargo: _________________________________________________________
  * Correo: ________________________________________________________

* **Validación de Seguridad:**
  * ¿El nivel de acceso solicitado es el mínimo necesario para las funciones? [ ] Sí [ ] No
    * Si respondiste "No", especifica cuál sería el adecuado: ________________
  * ¿Existen antecedentes de incumplimiento de confidencialidad del solicitante? [ ] Sí [ ] No
    * Si respondiste "Sí", detalla: _________________________________________
  * ¿Es necesaria una auditoría posterior periódica? [ ] Sí [ ] No

* **Decisión del Dueño:**
  * [ ] **Aprobado** — acceso autorizado completamente
  * [ ] **Aprobado con restricciones** — especifica: _______________________
  * [ ] **Rechazado** — motivo: __________________________________________

* **Observaciones adicionales:**
  _________________________________________________________________

**Firma del Dueño de la Información:** __________ **Fecha:** __/__/______

---

**SECCIÓN 7: VALIDACIÓN DE SEGURIDAD (Solo para datos críticos)**

**Para accesos a Módulo Financiero, Administrativo, o información clínica de menores, se requiere aprobación adicional del Oficial de Seguridad de la Información.**

* **Oficial de Seguridad:**
  * Nombre: ________________________________________________________
  * Correo: ________________________________________________________

* **Evaluación de Riesgo:**
  * Nivel de sensibilidad de datos accedidos: [ ] Bajo [ ] Medio [ ] Alto [ ] Crítico
  * ¿El solicitante ha completado entrenamiento en seguridad de datos? [ ] Sí [ ] No
    * Fecha de último entrenamiento: __/__/______
  * ¿Requiere autenticación multi-factor (MFA) adicional? [ ] Sí [ ] No

* **Decisión Final de Seguridad:**
  * [ ] **Aprobado sin condiciones**
  * [ ] **Aprobado con auditoría trimestral**
  * [ ] **Aprobado con MFA requerido**
  * [ ] **Rechazado por consideraciones de seguridad** — motivo: ____________

**Firma del Oficial de Seguridad:** __________ **Fecha:** __/__/______

---

**SECCIÓN 8: IMPLEMENTACIÓN TÉCNICA (USO EXCLUSIVO DE TI)**

Esta sección solo debe ser completada por el equipo técnico después de todas las aprobaciones.

* **Implementador Técnico:**
  * Nombre: ________________________________________________________
  * Correo: ________________________________________________________

* **Estado de la Solicitud:**
  * [ ] **Aprobada para Implementación** (todas las aprobaciones recibidas)
  * [ ] **Implementada** (acceso creado en el sistema)
  * [ ] **Rechazada** (razón técnica): ___________________________________

* **Detalles Técnicos:**
  * Fecha de Implementación: __/__/______
  * Hora: __ : __ (formato 24h)
  * Perfil de Acceso Creado: [ ] Sí [ ] No
    * Nombre del Perfil: _______________________________________________
    * ID de Usuario en Sistema: ________________________________________
  * Pasos ejecutados:
    1. _________________________________________________________________
    2. _________________________________________________________________
    3. _________________________________________________________________

* **Verificación Post-Implementación:**
  * ¿Se notificó al usuario? [ ] Sí [ ] No — Fecha: __/__/______
  * ¿El usuario confirmó funcionalidad? [ ] Sí [ ] No
    * Comentario del usuario: ___________________________________________
  * ¿Se registró en el historial de auditoría del sistema? [ ] Sí [ ] No

**Firma del Implementador:** __________ **Fecha:** __/__/______

---

**SECCIÓN 9: REGISTRO PERMANENTE DE AUDITORÍA**

Esta sección se completa automáticamente por el sistema y permanece como evidencia permanente.

| Campo | Valor |
| :--- | :--- |
| **Timestamp de Solicitud:** | [AAAA-MM-DD HH:MM:SS] |
| **IP de Origen:** | [Registrada automáticamente] |
| **Hash de Integridad del Formulario:** | [SHA-256 del formulario original] |
| **Decisión Final:** | Aprobada / Rechazada |
| **Fecha Resolución Final:** | [Cuando se cierra] |
| **Tiempo Total de Resolución:** | [Días hábiles] |
| **Incidentes de Seguridad Asociados:** | Ninguno / [Detallar] |
| **Próxima Auditoría Recomendada:** | [Fecha] |

---

### 3.3. Paso 3 — Flujo de Aprobación y Procedimiento Operativo

A continuación se describe el flujo completo de atención de la solicitud de acceso, desde que el usuario la registra hasta que recibe confirmación de acceso otorgado o rechazado. Este flujo está alineado con las mejores prácticas ITIL de Gestión de Solicitudes de Servicio.

#### 3.3.1. Diagrama Narrativo del Flujo (Descripción por Etapas)

**ETAPA 1: Ingreso de la Solicitud por el Usuario**

El usuario (terapeuta, administrativo, etc.) ingresa al portal de EduSync AI. En el menú principal, busca la opción **"Solicitudes > Solicitar Acceso a un Módulo"** o **"Mi Perfil > Ampliar Accesos"**. El sistema presenta el formulario EDS-ACC-001 adaptado dinámicamente según el perfil del usuario (ej. si es terapeuta, no ve la opción de Módulo Administrativo).

El usuario completa cada sección del formulario:
1. Sus datos personales (autocompletados si ya está logueado)
2. El módulo que necesita y el tipo de acceso
3. Justificación del negocio (campos de texto libre)
4. Vigencia del acceso

El usuario firma electrónicamente (o marca una casilla de consentimiento si es en plataforma web). El sistema genera automáticamente:
- Un **N.º de Solicitud único** (ej. EDS-ACC-0045-2025)
- Un **timestamp exacto** de cuándo se creó
- Un **registro en el historial de auditoría** del sistema

El sistema envía un correo de confirmación al usuario con el N.º de solicitud y un enlace para dar seguimiento en tiempo real. El correo indica: *"Tu solicitud ha sido registrada bajo el código EDS-ACC-0045-2025. Puedes ver su estado en tu bandeja de solicitudes. El ANS aplicable es: 24 horas hábiles"*.

**Responsable:** Usuario final

**Tiempo en esta etapa:** 5-10 minutos

---

**ETAPA 2: Revisión Automática por el Sistema**

Antes de enviar la solicitud a personas, el sistema ejecuta validaciones automáticas:
1. ¿Todos los campos obligatorios están completos? Si no, rechaza y pide que complete
2. ¿El usuario ya tiene un acceso activo a este módulo? Si sí, le ofrece opción de "modificar" en lugar de solicitar nuevo
3. ¿El acceso solicitado es coherente con el rol del usuario? (ej. un paciente no puede solicitar acceso al Módulo Financiero)
4. ¿El usuario tiene permisos base para estar en el sistema? (ej. ¿está activo? ¿contrato vigente?)

Si el sistema detecta que la solicitud puede resolverse automáticamente (ej. un acceso rutinario a reportes de un terapeuta sobre sus propios pacientes), puede ofrecer aprobación automática con un botón "Aceptar Términos" en lugar de esperar validación humana.

Si la solicitud pasa validaciones, se marca como **"Pendiente Aprobación Manual"** y avanza a la Etapa 3.

**Responsable:** Sistema automatizado (motor de reglas)

**Tiempo en esta etapa:** Instantáneo (< 1 segundo)

---

**ETAPA 3: Revisión por el Jefe Inmediato (Aprobación Nivel 1)**

El sistema notifica al jefe inmediato del solicitante (extraído de la base de datos) mediante un correo con asunto: *"Se requiere tu autorización: Solicitud de Acceso EDS-ACC-0045-2025"*. El correo incluye:
- Un resumen ejecutivo: quién solicita qué y para qué
- Un enlace directo a un portal web donde el jefe puede revisar, comentar y aprobar/rechazar
- El ANS parcial: cuánto tiempo tiene el jefe para responder (usualmente 4 horas = 75% del ANS total de 24 horas)

El jefe ingresa al portal, lee la justificación del negocio, valida que:
1. El acceso es coherente con las funciones del cargo del empleado
2. El empleado está actualmente bajo su supervisión
3. No hay conflictos de interés (ej. no está en proceso de desvinculación)

Si está conforme, hace clic en **"Autorizo"**, y opcionalmente agrega un comentario. Si no está conforme, hace clic en **"No Autorizo"** y debe especificar un motivo (campo obligatorio).

El sistema registra:
- La decisión (aprobado/rechazado)
- La identidad del jefe (usuario del sistema)
- La hora y fecha exacta
- El comentario (si lo hay)

Todo esto queda registrado permanentemente en el historial de auditoría.

**Responsable:** Jefe inmediato del solicitante

**Tiempo máximo (ANS):** 4 horas hábiles

**Qué ocurre si no responde en tiempo:** Al llegar al 75% del tiempo (3 horas), el sistema envía un recordatorio automático. Si llega a las 4 horas sin respuesta, la solicitud se **escala automáticamente** al Gerente del área (jefe del jefe) con una nota: *"No recibimos respuesta del jefe inmediato. La solicitud requiere revisión urgente"*.

---

**ETAPA 4: Validación por el Dueño de la Información (Aprobación Nivel 2)**

Una vez que el jefe inmediato aprueba, el sistema automáticamente asigna la solicitud al **Dueño de la Información** (Data Owner) según el módulo solicitado:
- Módulo de Reportes → Responsable de Terapeutas (Gerencia Clínica)
- Módulo Financiero → Administrador o Contador
- Módulo Administrativo → Gerente General

El Dueño recibe un correo con la solicitud completa, incluyendo la aprobación del jefe. El Dueño debe validar que:
1. El nivel de acceso solicitado es el **mínimo necesario** (Principio de Mínimo Privilegio)
2. El acceso no abre brechas de seguridad (ej. un terapeuta no debe ver reportes de otros terapeutas)
3. Hay justificación válida desde perspectiva de negocio

Por ejemplo, si un administrativo solicita acceso al Módulo Financiero, el Dueño verifica:
- ¿Está el solicitante autorizado a manipular dinero?
- ¿Bajo cuáles límites de operación? (ej. solo puede crear registros de hasta S/5,000)
- ¿Necesita exportar reportes o solo registrar?

El Dueño aprueba, aprueba con restricciones, o rechaza. Si hay restricciones, las especifica (ej. "Solo acceso de lectura, sin permisos de modificación").

Para solicitudes de **Módulo Financiero o Administrativo**, después de que el Dueño aprueba, el sistema automáticamente *escala a Oficiaía de Seguridad* (Etapa 5 adicional).

**Responsable:** Dueño de la Información (Data Owner) del módulo

**Tiempo máximo (ANS):** 12 horas hábiles (el 50% restante antes de las 24 horas)

---

**ETAPA 5: Validación de Seguridad (Solo para datos críticos)**

Para solicitudes de acceso a información sensible (datos clínicos, datos financieros, información de menores), el sistema remite la solicitud al **Oficial de Seguridad de la Información** (Chief Information Security Officer - CISO, o designado).

El Oficial de Seguridad:
1. Valida que el usuario haya completado entrenamientos obligatorios en confidencialidad y GDPR (aplica a menores)
2. Evalúa el perfil del usuario: ¿hay antecedentes de accesos indebidos?
3. Determina si se requiere **autenticación multi-factor (MFA)** adicional
4. Marca si se requiere **auditoría periódica** del acceso

El Oficial aprueba, aprueba con condiciones, o rechaza. Si rechaza, debe especificar razón (ej. "Usuario no ha completado capacitación de confidencialidad requerida").

**Responsable:** Oficial de Seguridad de la Información

**Tiempo máximo (ANS):** 4 horas hábiles (urgencia crítica)

---

**ETAPA 6: Ejecución Técnica por el Equipo de TI**

Una vez recibidas **todas las aprobaciones necesarias**, el sistema automáticamente genera una tarea para el equipo técnico (o es asignada a través de reglas de automatización). La tarea incluye:
- Especificación exacta de qué crear en el sistema
- Credenciales temporales (si aplica)
- Fecha efectiva del acceso
- Duración (si es temporal)

El técnico:
1. Crea el perfil de acceso en EduSync AI según las especificaciones
2. Registra credenciales temporales y envía al usuario (por canal seguro, nunca en correo)
3. Ejecuta la asignación de permisos en la base de datos
4. Registra la ejecución en el historial del sistema (automático mediante logging)
5. Realiza una **prueba** del acceso: verifica que el usuario pueda realmente acceder a los módulos aprobados

El técnico marca la tarea como **"Implementada"** en el sistema.

**Responsable:** Equipo Técnico (Administrador de Sistemas)

**Tiempo máximo (ANS):** 2 horas hábiles desde aprobación

---

**ETAPA 7: Notificación y Confirmación al Usuario**

El sistema envía un correo al usuario notificando que su acceso ha sido **habilitado exitosamente**. El correo incluye:
- Número de solicitud
- Qué acceso específico se otorgó
- Instrucciones de cómo usarlo
- Link a la Base de Conocimiento con tutoriales
- Fecha efectiva
- Si es temporal, fecha de expiración
- Contacto de soporte si tiene problemas

El mensaje es en **lenguaje amigable**, no técnico. Ejemplo:

> *"¡Excelente! Tu solicitud EDS-ACC-0045-2025 ha sido aprobada. A partir de hoy puedes acceder al Módulo de Reportes de Progreso de tus pacientes. Aquí te mostramos cómo hacerlo: [enlace a tutorial]. Tu acceso está activo hasta el 31 de diciembre de 2025. Si tienes problemas para entrar, contáctanos: soporte@edusyncai.pe"*

El usuario **confirma la recepción** haciendo clic en un botón "Confirmo que recibí el acceso" en el portal.

El usuario **prueba el acceso** (ingresa al módulo, verifica que puede ver lo que debe ver).

Si funciona correctamente, el usuario cierra la solicitud marcándola como **"Resuelta - Acceso Funcional"**.

**Responsable:** Sistema automatizado + Usuario final

**Tiempo en esta etapa:** 1-24 horas (depende del usuario)

---

**ETAPA 8: Cierre y Auditoría**

Una vez que el usuario confirma que el acceso funciona correctamente, la solicitud se cierra automáticamente. El sistema registra permanentemente:
- Toda la cadena de aprobaciones (quién aprobó qué y cuándo)
- La ejecución técnica (quién implementó y cuándo)
- El time-to-resolution (cuántos días/horas tomó todo el proceso)
- Si se cumplió el ANS

La solicitud queda **disponible indefinidamente** en el histórico de auditoría del sistema. Es una evidencia permanente de:
- Quién solicitó acceso
- Quién aprobó
- Quién implementó
- Cuándo se otorgó
- Qué acceso exactamente

Esto es crítico para cumplir con regulaciones de confidencialidad (especialmente importante con datos de menores) y para auditorías internas/externas.

**Responsable:** Sistema automatizado + Auditoría interna

**Tiempo:** Automático

---

#### 3.3.2. Diagrama Visual del Flujo

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FLUJO COMPLETO DE SOLICITUD                      │
│                          EDS-ACC-001-v1                              │
└─────────────────────────────────────────────────────────────────────┘

  [1. Usuario relena        [2. Validación       [3. Jefe Inmediato
       formulario]               automática]         revisa y aprueba]
         │                          │                       │
         ▼                          ▼                       ▼
   ┌──────────────┐         ┌────────────────┐    ┌──────────────────┐
   │ Portal Web   │──────→  │ Motor de Reglas│───→│ Notif. por correo│
   │ EduSync AI   │         │  (validación)  │    │  + Portal Web    │
   └──────────────┘         └────────────────┘    └──────────────────┘
         ▲                          ▲ SI                    ▼
         │ RECHAZO                  │                  Aprueba/Rechaza
         │ (incompleto)             │ NO                    │
         └──────────────────────────┘                       ▼
                                              ¿Datos críticos?
                                               /             \
                                            SÍ               NO
                                            │                 │
   ┌─────────────────────────────────────────┐               │
   │  [4. Dueño de Información valida]       │               │
   │  - Mínimo privilegio                    │               │
   │  - Coherencia de acceso                 │               │
   │  (12 horas máx)                         │               │
   └────┬────────────────────────────────────┘               │
        ▼                                                    │
   ┌──────────────────────────────────┐                     │
   │ [5. Oficial de Seguridad valida] │                     │
   │ - MFA requerido?                 │                     │
   │ - Auditoría periódica?           │                     │
   │ (4 horas máx)                    │                     │
   └────┬──────────────────────────────┘                    │
        │                                                   │
        └────────────────┬──────────────────────────────────┘
                         ▼
                 ¿Todas aprobadas?
                    /         \
                 SÍ              NO
                 │               │
                 │          ┌─────────────────┐
                 │          │ RECHAZO         │
                 │          │ Notificar usuario│
                 │          │ [CIERRE]        │
                 │          └─────────────────┘
                 │
                 ▼
        ┌──────────────────────────┐
        │ [6. Equipo TI Implementa]│
        │ - Crear perfil en BD     │
        │ - Asignar permisos       │
        │ - Registrar en logs      │
        │ (2 horas máx)            │
        └────┬─────────────────────┘
             ▼
        ┌──────────────────────────┐
        │ [7. Notif. a Usuario]    │
        │ - Acceso activo          │
        │ - Tutorial/documentación │
        │ - Usuario confirma       │
        └────┬─────────────────────┘
             ▼
        ┌──────────────────────────┐
        │ [8. CIERRE + AUDITORÍA]  │
        │ - Registro permanente    │
        │ - Verificación de ANS    │
        │ - Historial completo     │
        └──────────────────────────┘

   ANS TOTAL: 24 HORAS HÁBILES
```

---

#### 3.3.3. Tabla de Responsables y Tiempos

| Etapa | Responsable | Acción | Tiempo Máximo (ANS) | Qué Ocurre si Vence |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Usuario | Completar y enviar solicitud | N/A | Solicitud queda "Borrador" indefinidamente |
| 2 | Sistema | Validar integridad del formulario | 1 seg | Rechazar automáticamente con detalle de errores |
| 3 | Jefe Inmediato | Revisar y autorizar | 4 horas | Escalar al Gerente (jefe del jefe) |
| 4 | Dueño de Información | Validar seguridad y privilegios | 12 horas | Escalar al Gerente General + alerta CISO |
| 5 | Oficial de Seguridad | Validar cumplimiento | 4 horas | Rechazar automáticamente por incumplimiento |
| 6 | Equipo TI | Implementar en BD | 2 horas | Alerta escalar al CTO |
| 7 | Sistema + Usuario | Notificar y confirmar | 24 horas | Asumir acceso implementado; seguimiento manual |
| 8 | Sistema | Cerrar y registrar | 1 seg | Automático |

**TIEMPO TOTAL ANS (de punta a punta):** **24 horas hábiles** = desde que el usuario crea la solicitud hasta que recibe notificación de acceso otorgado o rechazado.

---

#### 3.3.4. Estructura Jerárquica de Aprobación por Tipo de Acceso

| Tipo de Solicitud | Módulo Afectado | Aprobación L1 | Aprobación L2 | Aprobación L3 (Seguridad) | ANS |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Acceso a Reportes de Mis Pacientes** | Reportes (Lectura) | Jefe Inmediato | NO requerida | NO requerida | 24h |
| **Acceso a Reportes + Exportación** | Reportes (Lectura + Descarga) | Jefe Inmediato | Gerente Clínico | NO requerida | 24h |
| **Acceso Financiero - Lectura** | Financiero (Solo Ver) | Jefe Inmediato | Contador | Oficial Seguridad | 12h |
| **Acceso Financiero - Edición** | Financiero (Registrar Pagos) | Jefe Inmediato | Administrador | Oficial Seguridad | 8h |
| **Acceso Administrativo** | Administrativo (Completo) | NO (debe ser superior) | Gerente General | Oficial Seguridad | 4h |
| **Acceso Crítico a Datos Clínicos** | Reportes Clínicos (Análisis) | Jefe Inmediato | Gerente Clínico | Oficial Seguridad | 8h |

---

### 3.4. Casos de Rechazo y Procedimiento

Es posible que una solicitud sea **rechazada** en algún punto del flujo. A continuación se detallan los escenarios de rechazo más comunes y cómo se procede:

**RECHAZO POR VALIDACIÓN AUTOMÁTICA:**
- El formulario está incompleto
- El usuario ya tiene activo el acceso solicitado
- El acceso solicitado no existe en el catálogo
- **Acción:** El sistema rechaza automáticamente y pide corrección. El usuario puede reenviar.

**RECHAZO POR JEFE INMEDIATO:**
- El jefe considera que el acceso no es necesario para el cargo
- El empleado está en proceso de desvinculación
- **Acción:** Se notifica al usuario. El usuario puede apelar escribiendo a Gerencia.

**RECHAZO POR DUEÑO DE INFORMACIÓN:**
- El nivel de acceso solicitado es mayor del necesario (violación de mínimo privilegio)
- No hay justificación válida de negocio
- **Acción:** Se notifica al usuario con razón específica. El usuario puede solicitar nuevamente con justificación mejorada.

**RECHAZO POR OFICIAL DE SEGURIDAD:**
- El usuario no ha completado entrenamientos obligatorios
- Hay antecedentes de violación de confidencialidad
- El acceso solicitado incumple regulaciones de protección de menores
- **Acción:** Se notifica al usuario. El usuario debe completar entrenamientos y esperar 30 días antes de reintentar.

En todos los casos de rechazo, el usuario recibe un correo con:
- Motivo específico del rechazo
- Pasos recomendados para reintentarlo
- Contacto de soporte para apelar

---

### 3.5. Caso de Uso: Ejemplo Completo en Contexto Real

**Escenario:** Martha Hernández, terapeuta del Centro, ingresa el 15 de marzo de 2025 y necesita acceso al Módulo de Reportes para ver el progreso de sus pacientes asignados.

| Tiempo | Responsable | Acción | Estado |
| :--- | :--- | :--- | :--- |
| 09:00 | Martha (Usuario) | Ingresa al portal, completa EDS-ACC-001, solicita acceso a Reportes (Lectura) de 5 pacientes | **Solicitud Creada** - EDS-ACC-0127-2025 |
| 09:02 | Sistema | Valida formulario: ✓ Completo, ✓ Usuario activo, ✓ Módulo existe | **Aprobación Automática - Escala a Jefe** |
| 09:15 | David López (Jefe) | Recibe correo de solicitud. Lee justificación: "Necesito ver progreso de mis pacientes para sesiones". Aprueba en portal | **Aprobado L1** |
| 09:30 | Sistema | Detecta: acceso a datos clínicos → requiere L2 + Seguridad | **Escala a Dueño de Información** |
| 10:45 | Dra. Carolina (Gerencia Clínica) | Recibe solicitud. Valida: Martha es terapeuta senior, acceso coherente, nivel de lectura es adecuado. Aprueba. | **Aprobado L2** |
| 11:00 | Sistema | Detecta: datos clínicos de menores → requiere validación de seguridad | **Escala a Oficial de Seguridad** |
| 11:30 | Lic. Roberto (Oficial Seguridad) | Verifica: Martha completó capacitación de confidencialidad el 10/03/2025 ✓, no hay antecedentes de vulneración ✓, menor de edad ✓. Aprueba sin MFA adicional. | **Aprobado L3** |
| 11:45 | Sistema | Todas las aprobaciones recibidas. Genera tarea técnica para TI | **Listo para Implementación** |
| 12:00 | Juan Martínez (Técnico TI) | Recibe tarea. Crea perfil "Martha_Reportes_Lectura" en BD, asigna permisos a 5 pacientes específicos, testa acceso. Marca como implementado. | **Implementado** |
| 12:30 | Martha | Recibe correo: "Tu acceso al Módulo de Reportes ha sido activado. Ingresa a [link]. Tu acceso está activo indefinidamente mientras sigas en el cargo." | **Notificada** |
| 13:00 | Martha | Accede al portal, verifica que ve 5 pacientes y puede descargar un reporte de prueba. Marca solicitud como "Resuelta - Acceso Funcional". | **CIERRE EXITOSO** |

**Tiempo Total:** 4 horas (dentro del ANS de 24 horas)

**Registro de Auditoría Permanente:**
```
EDS-ACC-0127-2025
- Solicitante: Martha Hernández (ID: TER-0045)
- Fecha Solicitud: 15/03/2025 09:00:00 (IP: 192.168.1.100)
- Módulo: Reportes (Lectura)
- Pacientes: [5 IDs específicos]
- Aprobaciones:
  * David López (Jefe) - 15/03/2025 09:15:00 - APROBADO
  * Dra. Carolina (Dueño Info) - 15/03/2025 10:45:00 - APROBADO
  * Lic. Roberto (Seguridad) - 15/03/2025 11:30:00 - APROBADO
- Implementación: Juan Martínez - 15/03/2025 12:00:00 - EXITOSA
- Perfil: Martha_Reportes_Lectura (Vigencia: Indefinida)
- Estado Final: CERRADA - 15/03/2025 13:00:00
- ANS Cumplido: SÍ (4 horas < 24 horas)
```

Este registro permanece en el sistema indefinidamente para futuras auditorías.

---

## 4. Análisis Técnico del Flujo de Auditoría Actual en EduSync AI

EduSync AI implementa un **sistema de auditoría en dos capas** que se integra con el procedimiento de solicitudes de servicio:

### 4.1. Capa 1: Auditoría de Sesiones Clínicas (Programado vs. Ejecutado)

El sistema compara automáticamente:
- **Programación:** Objetivos terapéuticos planificados (documento Word cargado por el terapeuta)
- **Ejecución:** Lo que realmente ocurrió en la sesión (transcripción de audio + fotos)

Resultado: Score de cumplimiento (0-100) que responde a la pregunta: *¿Qué tan bien se ejecutó lo planificado?*

### 4.2. Capa 2: Auditoría de Accesos y Cambios (Quién Hizo Qué y Cuándo)

El procedimiento EDS-ACC-001 establece:
- **Acceso Registrado:** Cada cambio de permiso queda documentado con identidad del solicitante, aprobadores, implementador
- **Trazabilidad Completa:** El sistema puede responder "¿quién otorgó acceso a Juan al módulo de pagos?" → "Aprobado por Dra. Carolina el 15/03/2025 a las 10:45"

---

## 5. Conclusiones

- **Primera:** La implementación de una plataforma estructurada de gestión de solicitudes de servicio transforma radicalmente la operación del Centro de Terapias. Las organizaciones que centralizan sus solicitudes reducen los costos operativos hasta en un **40%**, liberando al personal administrativo de tareas repetitivas para enfocarse en actividades de mayor valor.

- **Segunda:** El formato de solicitud de acceso (EDS-ACC-001) diseñado en este informe sigue las mejores prácticas ITIL: emplea lenguaje del usuario, solicita solo los datos estrictamente necesarios, exige justificación del negocio y contempla un flujo de aprobación multinivel que garantiza la seguridad y auditabilidad de los accesos otorgados.

- **Tercera:** El flujo de aprobación en ocho etapas (Ingreso, Validación Automática, Jefe Inmediato, Dueño de Información, Oficial de Seguridad, Ejecución Técnica, Notificación y Cierre) asegura que ningún acceso crítico sea otorgado sin la validación formal requerida, eliminando el riesgo de fallos de seguridad por falta de control.

- **Cuarta:** La inclusión del registro de auditoría permanente garantiza que la organización pueda responder en todo momento a las preguntas críticas: *"¿quién accede a la información de mis menores de edad?"*, *"¿quién otorgó acceso a los datos financieros?"*, *"¿cuándo se implementó este cambio?"*. Esto es un requisito no negociable en cualquier sistema que maneja información sensible de menores.

- **Quinta:** El ANS de 24 horas hábiles es realista y alcanzable para el Centro de Terapias (operación pequeña), permitiendo que los usuarios accedan rápidamente a herramientas sin comprometer validaciones de seguridad.

- **Sexta:** El procedimiento propuesto puede integrarse directamente como un anexo documental en el Avance de Proyecto Final (APF), demostrando competencias en Gestión de Sistemas de Información y cumplimiento de regulaciones de confidencialidad aplicables en la carrera de Ingeniería de Sistemas.

- **Séptima:** La automatización del flujo (reglas de asignación, escalamientos automáticos, notificaciones, validaciones) reduce significativamente la carga administrativa y minimiza errores manuales. Un seguimiento manual de estas solicitudes tomaría entre 30-60 minutos por solicitud; automatizado, el sistema invierte < 1 segundo en las validaciones que pueden hacerse sin intervención humana.

---

## 6. Recomendaciones de Implementación

### 6.1. Implementación Rápida (MVP - Mínimo Producto Viable)

**Fase 1 (Semana 1):** Implementar validación automática + flujo de aprobación manual vía correo
**Fase 2 (Semana 2):** Portal web para aprobadores (en lugar de correo)
**Fase 3 (Semana 3):** Auditoría permanente + reportes de cumplimiento de ANS

### 6.2. Integración con RGPD / Ley de Protección de Menores en Perú

- Agregar campo "Validación de RGPD" en Sección 7 (Seguridad)
- Requerir consentimiento explícito de padres si el acceso incluye ver historiales de menores

### 6.3. Capacitación Requerida

- **Aprobadores (Jefes, Gerentes):** 1 hora de capacitación en criterios de aprobación
- **Usuarios finales:** 30 min en cómo completar el formulario
- **Técnicos:** 2 horas en procedimiento de implementación e historial de auditoría

---

## 7. Referencias

* Universidad Tecnológica del Perú. (2025). Semana 10, Sesión 2: Gestión de Solicitudes de Servicio — Herramientas y Mejores Prácticas. Material de clase, Curso Integrador II: Sistemas.
* AXELOS. (2019). ITIL 4 Foundation. TSO (The Stationery Office).
* Hunnebeck, L. (2011). ITIL Service Design. TSO.
* Centro de Terapias Juan Pablo II. (2024). Documento de Proyecto: EduSync AI. Repositorio interno.
* ISO/IEC 27001:2022. Información security management systems. International Organization for Standardization.
* GDPR — Regulation (EU) 2016/679. Protection of natural persons with regard to the processing of personal data. European Union.
* Ley N° 29733 - Ley de Protección de Datos Personales (Perú). Diario Oficial El Peruano.

---

**Documento Versión 1.0**
**Autor:** Equipo de Proyecto EduSync AI | UTP Curso Integrador II: Sistemas
**Fecha:** 27 de mayo de 2025
**Clasificación:** Proyecto Académico - Uso Interno

---

### ANEXO A: Checklist de Implementación

- [ ] Diseño de base de datos para tabla `AccessRequest` con campos de la Sección 0-9
- [ ] Desarrollo del formulario dinámico (frontend Angular con validaciones)
- [ ] API REST para crear, actualizar, obtener solicitudes (`/api/access-requests`)
- [ ] Motor de reglas para validación automática (Etapa 2)
- [ ] Motor de asignación automática (asignar a jefe inmediato, dueño, seguridad)
- [ ] Sistema de notificaciones por correo (usando plantillas)
- [ ] Portal web para aprobadores (dashboard de solicitudes pendientes)
- [ ] Logs de auditoría (registrar cada acción con timestamp, usuario, IP)
- [ ] Reportes de ANS (cumplimiento, demoras, tendencias)
- [ ] Documentación de usuario (tutoriales, FAQ, guía del jefe)
- [ ] Pruebas de seguridad (validar que no hay escalación de privilegios)
- [ ] Capacitación del equipo

---

### ANEXO B: Plantilla de Correo de Notificación

**Asunto:** Tu solicitud de acceso ha sido autorizada — EDS-ACC-0127-2025

Estimada Martha,

¡Excelente noticia! Tu solicitud de acceso al Módulo de Reportes y Análisis ha sido **aprobada y activada exitosamente**.

**Detalles de tu acceso:**
- **Número de Solicitud:** EDS-ACC-0127-2025
- **Módulo:** Reportes y Análisis de Progreso
- **Nivel de Acceso:** Lectura + Descarga de Reportes
- **Pacientes Asignados:** 5 (ver lista en el portal)
- **Vigencia:** Indefinida (mientras ocupes tu cargo)
- **Fecha de Activación:** 15 de marzo de 2025, 12:00 p.m.

**Cómo Acceder:**
1. Ingresa a [https://edusyncai.pe]
2. Con tus credenciales habituales
3. En el menú principal, selecciona "Análisis > Mis Pacientes"
4. Verás el dashboard con el progreso de tus 5 pacientes

**Primeros Pasos:**
- Tutorial interactivo (5 min): [enlace]
- FAQ - Preguntas Frecuentes: [enlace]
- Video: "Cómo descargar un reporte" [enlace]

Si tienes problemas técnicos, contacta a nuestro equipo de soporte:
- **Email:** soporte@edusyncai.pe
- **WhatsApp:** +51 968 123 456
- **Horario:** L-V, 8 AM - 6 PM

¿Preguntas sobre tu acceso? Responde a este correo.

Un saludo,
**Equipo de Tecnología | Centro de Terapias Juan Pablo II**

---

*Este correo fue generado automáticamente por EduSync AI. No responder a este correo.*

