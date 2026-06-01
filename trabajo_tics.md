### **Semana 09 - Sesión 1: Gobierno del Plan de Continuidad de Negocio (Parte I)**

**Temas Tratados:**

* 
**Fundamentos:** Introducción al Gobierno del Plan de Continuidad de Negocio (PCN) en el contexto de las TICs.


* 
**Normativas:** Establecimiento de un marco de gobierno TIC, incluyendo políticas y normativas para garantizar la continuidad.


* 
**Evaluación y Riesgos:** Desarrollo de un Análisis de Impacto al Negocio (BIA) con enfoque TIC y la respectiva gestión de riesgos.


* 
**Recuperación:** Diseño de estrategias de continuidad y recuperación tecnológica (Proteger, Garantizar, Generar).



**Aplicación a un Proyecto:**
Si estás desarrollando una aplicación de Business Intelligence estructurada en esquema estrella con Next.js y SQL, puedes utilizar el Análisis de Impacto al Negocio (BIA) para identificar qué perspectivas (por ejemplo, el tablero financiero o el de clientes) son absolutamente críticas. Con esto, puedes diseñar una estrategia de recuperación tecnológica específica que determine qué bases de datos deben restaurarse primero en caso de un fallo en el servidor.

---

### **Semana 09 - Sesión 2: Gestión, Validación y Mejora Continua del PCN-TIC**

**Temas Tratados:**

* 
**Gestión de Crisis:** Protocolos para la activación del Comité de Crisis TIC y gestión de la comunicación tanto interna (con el personal) como externa (con clientes y reguladores).


* 
**Pruebas y Simulacros:** Metodología de validación dividida en 4 niveles: Revisión Documental (Nivel 1), Prueba Funcional (Nivel 2), Simulacro Completo (Nivel 3) y Prueba de Interrupción (Nivel 4).


* 
**Monitoreo y Mejora Continua:** Medición de la efectividad mediante KPIs como un objetivo de disponibilidad del 99.9%, RTO (Recovery Time Objective) menor a 4 horas y MTTR (Mean Time to Recovery) de 45 minutos, apoyados en el ciclo PDCA (Planificar, Hacer, Verificar, Actuar).


* 
**Documentación:** Creación de una pirámide de gestión del conocimiento de 4 niveles que abarca el Manual del PCN-TIC, Políticas/Procedimientos, Guías/Checklists y Registros/Evidencias.


* 
**Cumplimiento e Integración:** Alineación con normativas (como la Ley N.° 29733 de Protección de Datos Personales o ISO 22301) y la integración del PCN como un componente central del Plan Estratégico de TI (PETI).



**Aplicación a un Proyecto:**
En la arquitectura de un sistema ERP que integra modelos de IA locales para un centro de terapias, es vital establecer un ciclo PDCA y definir KPIs estrictos, como el MTTR, para garantizar que el módulo de registros o controles biométricos vuelva a estar en línea rápidamente tras una caída. Además, implementar la pirámide documental te permitirá estandarizar manuales y checklists operativos, asegurando que cualquier colaborador de tu equipo en Piura o Talara sepa exactamente qué pasos seguir para reiniciar los servicios backend en Flask sin depender de una sola persona.

---

### **Semana 10: Plan de Pruebas y Ejercicios de Continuidad**

**Temas Tratados:**

* 
**Importancia Crítica:** Reconocimiento de que las organizaciones dependen de los sistemas de información para sus operaciones críticas y que eventos como desastres naturales, ciberataques o errores humanos pueden paralizarlas.


* 
**Planes de Respaldo:** La necesidad de desarrollar un Business Continuity Plan (BCP) y un Disaster Recovery Plan (DRP).


* 
**Validación de Efectividad:** La premisa de que tener los planes documentados no es suficiente; es obligatorio verificar su efectividad periódicamente mediante pruebas y ejercicios prácticos de continuidad.



**Aplicación a un Proyecto:**
Para asegurar la resiliencia de un repositorio o despliegue en la nube, puedes agendar "Pruebas Funcionales" semestrales. Por ejemplo, puedes simular una pérdida de conexión con la base de datos principal o un error humano en un *commit* reciente, ejecutando los pasos de recuperación en un entorno de *staging* para confirmar que tu DRP funciona sin afectar las operaciones de los usuarios finales.