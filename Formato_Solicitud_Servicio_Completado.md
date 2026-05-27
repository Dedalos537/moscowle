# 📋 Formato de Solicitud de Servicio
## Gestión de Solicitudes de Información y Acceso | Facultad de Ingeniería | Semana 10

*Código: SS-UTP-2025 | Versión: 1.0 | Revisión: 001*

---

### Instrucciones para el Equipo

- Este formato está diseñado para documentar formalmente las solicitudes de servicio según los lineamientos de ITIL 4 [^1].
- Recuerda que una solicitud de servicio NO es un incidente.
- Las solicitudes son peticiones planificadas y anticipadas para obtener información, acceso u otros recursos del Catálogo de Servicios [^2].
- Complete todos los campos con información real y coherente.
- Si un campo no aplica a su caso, escriba "N/A" y justifique brevemente.
- El formato debe estar firmado por todos los aprobadores requeridos antes de ser entregado.

---

## 📌 Sección 1 | Identificación de la Solicitud

| Campo | Detalle |
| :--- | :--- |
| **N.° de Solicitud:** | SS-2025-001 |
| **Fecha de Solicitud:** | 15 / 05 / 2025 |
| **Hora de Registro:** | 10:30 (formato 24 h) |
| **Canal de Solicitud:** | Portal Web |
| **Nombre del Proyecto:** | EduSync AI — Sistema de Gestión Integral para Centros de Terapia |
| **Código del Proyecto:** | MOS-2025-UTP |

---

## 👤 Sección 2 | Datos del Solicitante

| Campo | Detalle |
| :--- | :--- |
| **Nombre Completo:** | Quispe Mamani, Alberto Rafael |
| **Código de Estudiante:** | U20241834 |
| **Correo Institucional:** | alberto.quispe@utp.edu.pe |
| **Ciclo / Sección:** | 2025-1 / Sección B |
| **Teléfono de Contacto:** | +51 987 654 321 |
| **Rol en el Proyecto:** | Líder de Proyecto |
| **Nombre del Docente:** | Mg. Ing. Carlos Mendoza López |

---

## 🏷️ Sección 3 | Clasificación de la Solicitud

> Según ITIL 4, una solicitud de servicio es una petición formal de un usuario para que se le provea algo que forma parte de la entrega normal del servicio [^3].

- **Tipo de Solicitud:** De Información y De Acceso
- **Subcategoría:**
  - *De INFORMACIÓN:* Solicitud de manuales o documentación técnica
  - *De ACCESO:* Nuevo acceso a sistema o módulo
- **Prioridad:** Alta

---

## 📝 Sección 4 | Descripción Detallada de la Solicitud

> Esta sección es el núcleo del formato. Proporcione información suficientemente detallada para que el equipo pueda comprender qué se necesita, por qué y las condiciones esperadas de entrega [^4].

### 4.1 Descripción de la Solicitud

Se solicita acceso al módulo de configuración del sistema EduSync AI y la documentación técnica de la API REST para la integración del módulo de juegos terapéuticos con clasificador SVM. El acceso requerido incluye:

- Credenciales de administrador para el entorno de pruebas (staging)
- Documentación de endpoints REST del blueprint `/api/games/*`
- Acceso a la base de datos MySQL para consultar las tablas `SessionMetrics` y `Game`
- Repositorio del modelo SVM entrenado (`ai_models/svm_model.pkl`)

### 4.2 Justificación Académica

El equipo se encuentra en el Sprint 4 del cronograma del proyecto (Semanas 7-8), cuya entrega principal es la implementación del clasificador SVM para ajuste automático de dificultad de juegos terapéuticos y la generación de reportes automáticos. Sin acceso al entorno de pruebas y a la documentación de la API, no es posible completar la integración del backend Flask con el frontend Angular 20. El impacto de no atender esta solicitud implica el retraso de la entrega del Sprint 4 y la imposibilidad de realizar las pruebas de integración del módulo de IA.

### 4.3 Usuarios Afectados o Beneficiados

- 2 desarrolladores backend (integración API Flask + modelo SVM)
- 1 desarrollador frontend (componentes Angular para visualización de métricas)
- 1 terapeuta (pruebas de usuario del módulo de juegos)
- Impacto directo: 4 personas | Impacto indirecto: 5 terapeutas + 60-80 pacientes

### 4.4 Recursos o Sistemas Involucrados

- **Backend:** Flask 2.3 con blueprint `api_bp` (endpoints `/api/games/*`, `/api/sessions/*`)
- **Frontend:** Angular 20 SPA (módulo de juegos terapéuticos)
- **Base de datos:** MySQL (tablas `User`, `Appointment`, `SessionMetrics`, `Game`, `AppointmentGame`)
- **Modelo ML:** Scikit-learn SVM con kernel RBF (archivo `ai_models/svm_model.pkl`)
- **Infraestructura:** Railway.app (producción) + Servidor cPanel (staging)
- **Servicios externos:** Groq API (asistente conversacional), Google Drive API (respaldos)

### 4.5 Fecha Requerida de Atención

22 / 05 / 2025 — Urgente: El Sprint 4 finaliza la semana del 26/05 y las pruebas de integración requieren al menos 3 días hábiles.

---

## 🔐 Sección 5 | Detalle de Acceso

*(Completar solo si la solicitud es De Acceso)*

| Campo | Detalle |
| :--- | :--- |
| **Sistema o Aplicación:** | EduSync AI — Panel de Administración |
| **URL / Ruta de Acceso:** | https://staging.moscowle.centrojuanpabloii.com/admin |
| **Tipo de Permiso Solicitado:** | Administrador (configuración de juegos, gestión de usuarios, acceso a métricas) |
| **Nivel de Acceso Requerido:** | Módulos: Games (CRUD + configuración SVM), Users (solo lectura), Reports (generación y descarga), Sessions (visualización completa) |
| **Dueño del Sistema:** | Administrador del Centro de Terapias Juan Pablo II |
| **Fecha Inicio / Expiración:** | De: 15/05/2025 Hasta: 30/06/2025 |

### Justificación de Seguridad

El nivel de acceso Administrador es necesario para configurar los parámetros del clasificador SVM (umbrales de dificultad, pesos del modelo) y para asignar juegos a sesiones de terapia. Se implementarán las siguientes medidas de seguridad:

- Autenticación con bcrypt y tokens JWT con expiración de 8 horas
- Rate limiting de 20 solicitudes por minuto para endpoints sensibles
- Todas las conexiones vía HTTPS forzado (Flask-Talisman)
- Registro de auditoría en Sentry para todas las acciones de configuración
- El acceso expirará automáticamente el 30/06/2025, posterior a la finalización del ciclo académico

---

## ✅ Sección 6 | Flujo de Aprobación

| Aprobador / Rol | Nombre y Firma | Fecha de Aprobación | Decisión |
| :--- | :--- | :--- | :--- |
| **Jefe Inmediato / Líder de Proyecto** | Alberto Quispe Mamani | 15/05/2025 | Aprobado |
| **Administrador del Sistema** | [Pendiente] | [Pendiente] | [ ] Aprobado / [ ] Rechazado |
| **Responsable de TI / Mesa de Ayuda** | [Pendiente] | [Pendiente] | [ ] Aprobado / [ ] Rechazado |

### Observaciones del Proceso de Aprobación

*[En caso de rechazo, indique el motivo y las condiciones para que la solicitud pueda ser reformulada. En caso de aprobación condicional, especifique las restricciones.]*

---

## ⏱️ Sección 7 | Acuerdo de Nivel de Servicio (SLA)

| Prioridad | Tiempo Estimado de Atención | Estado de Cumplimiento |
| :--- | :--- | :--- |
| **Alta** (afecta operación crítica) | 4 horas hábiles | [ ] Dentro del SLA / [ ] Fuera del SLA |
| **Media** (impacto moderado) | 1 día hábil | [ ] Dentro del SLA / [ ] Fuera del SLA |
| **Baja** (mejora o consulta) | 3 días hábiles | [ ] Dentro del SLA / [ ] Fuera del SLA |

- **Prioridad Asignada a esta Solicitud:** Alta — afecta la entrega del Sprint 4 del proyecto académico
- **Responsable de Atención (TI):** [Nombre del integrante encargado]
- **Fechas:** Inicio: [DD / MM / AAAA] | Real de Cierre: [DD / MM / AAAA]

---

## 📊 Sección 8 | Registro de Cumplimiento y Cierre

- **Estado Final de la Solicitud:** [ ] Atendida satisfactoriamente / [ ] Atendida parcialmente / [ ] Rechazada / [ ] Cancelada por el solicitante

### Detalle de la Solución Brindada

*[Describa de forma concisa cómo se atendió la solicitud: qué se entregó, qué permisos se otorgaron, qué información se proporcionó. Incluya referencias a tickets, correos o documentos adjuntos si aplica.]*

### Evidencias de Cumplimiento

*[Liste las evidencias que acreditan la atención de la solicitud (capturas de pantalla, correos, registros del sistema, etc.).]*

- **Calificación del Servicio por el Solicitante:** [ ] Excelente / [ ] Bueno / [ ] Regular / [ ] Deficiente

### Comentarios del Solicitante

*[Observaciones adicionales sobre la calidad y oportunidad del servicio recibido.]*

- **Firma del Solicitante:** _______________________ (Nombre: _________________ Fecha: _____________)
- **Firma de Resp. TI:** _______________________ (Nombre: _________________ Fecha: _____________)

---

## 🧠 Sección 9 | Reflexión del Equipo (Sustentación Académica)

### 9.1 ¿Cómo diferencia su equipo una Solicitud de Información de una Solicitud de Acceso en el contexto de su proyecto?

En el proyecto EduSync AI, una **Solicitud de Información** corresponde a peticiones de documentación técnica o datos que no implican modificar permisos en el sistema. Por ejemplo, solicitar el manual de la API REST de juegos terapéuticos o consultar el esquema de la base de datos para conocer la estructura de la tabla `SessionMetrics`. Una **Solicitud de Acceso**, en cambio, implica otorgar credenciales o permisos para operar sobre el sistema. Por ejemplo, crear un usuario administrador para configurar los parámetros del clasificador SVM, o asignar permisos de escritura en el módulo de pagos para registrar transacciones Yape.

La diferencia clave está en el **impacto sobre la seguridad**: las solicitudes de acceso requieren aprobación del administrador del sistema y del responsable de TI, mientras que las de información pueden ser resueltas por la mesa de ayuda con la documentación existente.

### 9.2 ¿De qué manera este formato garantiza la seguridad y trazabilidad de la información del proyecto?

El formato implementa cuatro mecanismos de seguridad y trazabilidad:

1. **Segmentación de aprobaciones (Sección 6):** La solicitud requiere la firma de tres roles distintos (líder de proyecto, administrador del sistema, responsable de TI), lo que asegura que ningún cambio de acceso se realiza sin la supervisión adecuada. Esto se alinea con el control A.9.2.1 de ISO 27001 (Registro y baja de usuarios).

2. **Justificación de seguridad obligatoria (Sección 5):** Al exigir una explicación del porqué del nivel de acceso solicitado y las medidas de mitigación, se aplica el principio de "need-to-know" (mínimo privilegio). En EduSync AI, esto evita que un desarrollador acceda a datos financieros sensibles cuando solo necesita trabajar con métricas de juegos.

3. **SLA con priorización (Sección 7):** Los tiempos de atención diferenciados por prioridad permiten que las solicitudes críticas (como un acceso de emergencia para restaurar un servicio) se atiendan en 4 horas, mientras que las consultas menores tienen 3 días. Esto garantiza que los recursos de TI se asignen según el impacto.

4. **Registro de cumplimiento y evidencias (Sección 8):** La sección de cierre documenta qué se entregó, cuándo y con qué evidencias, creando un registro de auditoría completo. Esto permite rastrear quién tuvo acceso a qué recurso y por cuánto tiempo, fundamental para la trazabilidad exigida por ITIL 4.

### 9.3 ¿Qué ajustes realizaría al formato para adaptarlo mejor a las características específicas de su proyecto?

**Ajuste 1 — Niveles de acceso por módulo granular.** El formato actual define el permiso como Lectura/Escritura/Administrador, pero EduSync AI tiene 12 blueprints con permisos diferenciados por rol (admin, terapista, jugador). Se agregaría una tabla donde cada módulo del sistema tenga su propio nivel de acceso solicitado, similar al Anexo C del documento del proyecto (matriz de roles y permisos).

**Ajuste 2 — Integración con el motor de flujo de trabajo inteligente.** El sistema EduSync AI incluye un `workflow_engine` que escanea el estado del sistema y genera acciones inteligentes. Se podría agregar un campo que indique si la solicitud fue generada automáticamente por el motor o es manual, y si el motor puede ejecutarla sin intervención humana. Esto alinea el formato con la automatización de procesos de ITIL 4.

**Ajuste 3 — Campo para recursos cloud y APIs externas.** EduSync AI se integra con Groq API, Google Gemini, Google Drive y Gmail SMTP. Una solicitud de acceso podría involucrar tokens de API o credenciales OAuth2. Se agregaría una subsección para especificar el tipo de recurso externo, el proveedor y las políticas de rotación de credenciales, siguiendo el control A.9.4.2 de ISO 27001.

---

## 📚 Sección 10 | Historial de Versiones del Formato

| Ver. | Fecha | Descripción del Cambio | Elaborado por |
| :--- | :--- | :--- | :--- |
| **1.0** | 2025 | Versión inicial del formato — Semana 10, Sesión 1 | Docente del Curso |
| **1.1** | 15/05/2025 | Completado con datos del proyecto EduSync AI — Centro de Terapias Juan Pablo II | Alberto Quispe Mamani — Líder de Proyecto |

---

*Gestión de Servicios de TI — Facultad de Ingeniería | Universidad Tecnológica del Perú | 2025*

---

## 🔗 Diagrama del Flujo de Atención de Solicitudes (Moscowle IA)

```mermaid
flowchart LR
    accTitle: Flujo de atención de solicitudes de servicio EduSync AI
    accDescr: Muestra el flujo desde la recepción de la solicitud hasta el cierre, pasando por clasificación, aprobación y atención

    A["📥 Recibir solicitud"]
    B["📋 Clasificar tipo<br/>(Información / Acceso)"]
    C{"¿Requiere<br/>aprobación?"}
    D["📩 Enviar a aprobadores<br/>(Sección 6)"]
    E{"¿Aprobada?"}
    F["🔧 Atender solicitud<br/>(asignar recursos)"]
    G["📤 Entregar respuesta<br/>(documentación / acceso)"]
    H["✅ Registrar cierre<br/>(Sección 8)"]
    I["❌ Rechazar y notificar<br/>con observaciones"]
    J["📊 SLA en monitoreo"]

    A --> B
    B --> C
    C -->|"Sí"| D
    C -->|"No"| F
    D --> E
    E -->|"Sí"| F
    E -->|"No"| I
    F --> J
    J --> G
    G --> H
    I --> H

    classDef start fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#1e3a5f
    classDef process fill:#fef9c3,stroke:#ca8a04,stroke-width:2px,color:#713f12
    classDef decision fill:#fce7f3,stroke:#db2777,stroke-width:2px,color:#831843
    classDef end fill:#dcfce7,stroke:#16a34a,stroke-width:2px,color:#14532d
    classDef reject fill:#fee2e2,stroke:#dc2626,stroke-width:2px,color:#991b1b

    class A start
    class B,F,J,G process
    class C,E decision
    class H end
    class I reject
```

---

## 📖 Referencias

[^1]: AXELOS. (2019). *ITIL Foundation: ITIL 4 Edition*. The Stationery Office.
[^2]: ISO/IEC 20000-1:2018. *Information technology — Service management — Part 1: Service management system requirements*.
[^3]: Cannon, D. (2016). *ITIL Service Strategy*. The Stationery Office.
[^4]: ISO/IEC 27001:2022. *Information security, cybersecurity and privacy protection — Information security management systems — Requirements*.
