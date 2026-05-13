Semana 8 - Sesión 1: Validación del Servicio y
Verificación de Requerimientos

Mg. Ing. Luis Gonzaga Neira Ayala

La Tragedia del Requerimiento Perfecto

Imagina  que  construyes  el  sistema  de  seguridad  más

avanzado para un banco en Piura. El código no tiene errores,

la  encriptación  es  militar  y  el  sistema  nunca  se  cae

(Verificación técnica: 100/100). Pero, al entregarlo, el cajero

nota que el sistema tarda 30 segundos en abrir la gaveta de

efectivo  por  cada  cliente.  El  software  es  perfecto,  pero  el

negocio está perdiendo dinero.

INICIO

Presentación del Logro

Al finalizar la sesión, el estudiante diseña y ejecuta un plan de pruebas

de  validación  y  verificación  de  requerimientos,  distinguiendo  entre

pruebas  funcionales  y  no  funcionales,  mediante  el  uso  de  casos  de

prueba  prácticos,  con  la  finalidad  de  garantizar  que  el  servicio  de

software  cumpla  con  las  expectativas  del  cliente  y  los  estándares  de

calidad técnica.

INICIO

¿Por qué es vital esta sesión?

En  el  entorno  empresarial  (Aseguramiento  de  la  Calidad):  Las  compañías  de
desarrollo de software invierten entre el 30% y 40% de su presupuesto total en el área
de QA (Garantía de Calidad).
Impacto Financiero: Un error identificado en la etapa de Producción (cuando el usuario
ya  usa  el  sistema)  puede  resultar  hasta  100  veces  más  costoso  de  reparar  que  uno
detectado en la fase de diseño o pruebas iniciales.
Relevancia Académica: Esta sesión te entrega la metodología para elaborar el Informe
de  Pruebas,  el  cual  es  un  componente  obligatorio  para  tu  Avance  de  Proyecto  Final  2
(APF2).
Valor para el Negocio: Sin un proceso de validación, no existe evidencia técnica ni
funcional de que el sistema realmente resuelva los problemas del cliente o sea apto para
el mercado.

UTILIDAD

Transformación

El Modelo en V
Este modelo es el estándar de la industria para entender que por cada fase de creación, debe existir una fase
de validación.

Lado Izquierdo (Verificación):

Se  enfoca  en  el  proceso  técnico.  La  pregunta  clave  es:  ¿Estamos  construyendo  el  producto
correctamente?. Aquí aseguramos que el código siga las reglas y el diseño inicial.
Se  trata  de  evaluar  los  procesos  técnicos  y  matemáticos.  Consiste  en  revisar  el  código  fuente,  la
arquitectura de la base de datos y la lógica de los algoritmos sin necesidad de ejecutar el sistema por
completo.

Lado Derecho (Validación):

Se enfoca en el valor del negocio. La pregunta clave es: ¿Estamos construyendo el producto correcto?.
Aquí aseguramos que el usuario final realmente pueda usar la herramienta para sus necesidades.
Se trata de evaluar el nivel de satisfacción y utilidad. Aquí el sistema informático se ejecuta en un
entorno real o simulado para garantizar que resuelve el problema original del cliente.

TRANSFORMACIÓN

Transformación

TRANSFORMACIÓN

Transformación

Pruebas Funcionales vs. No Funcionales
A. Pruebas Funcionales (Evaluación de Comportamiento)

Evalúan el "Qué" hace el sistema. Se basan en proporcionar datos de entrada y observar si las
salidas coinciden con lo exigido en el documento de requisitos. También se conocen como pruebas
de "caja negra" porque el evaluador no necesita conocer la estructura del código interno, solo el
resultado.

Pruebas de Límites: ¿Qué sucede si un campo de edad recibe el número 999 o el número -5?
Pruebas de Integración de Módulos: En un sistema educativo, si el profesor de ciencias
ingresa una nota en su registro, ¿esa nota se refleja automáticamente en la libreta consolidada
del estudiante?
Pruebas de Trayectoria Principal: El flujo ideal. Ingresar usuario, ingresar contraseña correcta
y acceder a la pantalla principal sin interrupciones.

TRANSFORMACIÓN

Transformación

Pruebas Funcionales vs. No Funcionales
B. Pruebas No Funcionales (Atributos de Calidad)
Evalúan el "Cómo" trabaja el sistema. Un programa puede cumplir todas sus funciones, pero si falla en estos
atributos, será rechazado por el mercado.

Rendimiento y Carga: ¿Cómo se comporta el sistema bajo presión? Por ejemplo, medir el tiempo de
respuesta cuando 500 estudiantes intentan matricularse exactamente a la misma hora.
Usabilidad (Facilidad de uso): ¿El sistema es intuitivo? Si un administrador necesita realizar quince
pasos distintos en la pantalla para dar de alta a un nuevo empleado, el sistema genera fatiga operativa.
Seguridad y Control de Acceso: Garantizar que un usuario con perfil de "estudiante" no pueda alterar
la dirección de internet (enlace) en su navegador para acceder a las pantallas con privilegios de
"director".
Portabilidad: Asegurar que el portal informático funcione y sea legible tanto en el monitor panorámico
de una computadora de escritorio como en la pantalla reducida de un teléfono móvil.

TRANSFORMACIÓN

Transformación
Casos de Estudio Adicionales para Análisis en Clase
Para que la teoría cobre vida, analizamos dónde falló el proceso en escenarios reales:
Caso 1: El Sistema Biométrico Escolar (Fallo de Validación del Entorno)

institución  educativa  contrata  el  desarrollo  de  un  sistema  de
Situación:  Una
reconocimiento  facial  automático  para  registrar  la  asistencia  de  los  alumnos.  Las
pruebas  de  laboratorio  indican  una  precisión  del  99%  al  identificar  los  rostros  y
guardarlos en la base de datos (Verificación correcta).
El Problema: El primer día de clases, el sistema es instalado en el pasillo principal del
colegio.  A  las  6:30  a.m.,  la  falta  de  luz  natural  en  ese  pasillo  impide  que  las  cámaras
reconozcan a los alumnos, generando una fila interminable en la puerta.
Lección:  Falló  la  Validación.  El  equipo  técnico  construyó  un  modelo  matemático
perfecto,  pero  jamás  evaluó  el  producto  en  las  condiciones  ambientales  reales  del
usuario.

TRANSFORMACIÓN

Transformación

Caso 2: El Asistente de Evaluación Automatizada (Fallo de Mantenibilidad)

Situación:  Se  diseña  una  herramienta  inteligente  para  leer  los  exámenes  de  los
alumnos y calificarlos automáticamente. Funciona a la perfección durante el primer
mes (Verificación y Validación correctas).
El  Problema:  El  Ministerio  de  Educación  solicita  un  cambio  menor  en  la  escala  de
calificaciones. Al intentar hacer esta pequeña modificación, el equipo descubre que
todo  el  código  fue  escrito  en  un  solo  bloque  gigantesco,  sin  comentarios,  sin
módulos  separados  y  sin  documentación.  Modificar  una  línea  rompe  todo  el
programa.
Lección: Falló la Prueba No Funcional (Mantenibilidad). El sistema informático debe
estar  preparado  para  evolucionar  y  ser  modificado  de  manera  estructurada  en  el
futuro.

TRANSFORMACIÓN

🚀 PRÁCTICA

1. Matriz  de  Validación  de  Requerimientos:  Una  tabla  que  cruce  los  requerimientos  del

cliente con el tipo de prueba (Funcional/No Funcional).

2. Diseño de Casos de Prueba (Mínimo 5).
3. ID, Descripción, Precondición, Pasos, Resultado Esperado y Resultado Obtenido.
4. Registro de Defectos (Bugs): Descripción de qué falló durante la ejecución y cuál es el plan

de corrección.

5. Certificado de Aceptación (Simulacro): Un breve párrafo donde se indique si el servicio está

"Apto" para despliegue basado en los resultados.

PRÁCTICA

🏁 Cierre

Verificación técnica; Validación es satisfacción del cliente.

Un plan de pruebas debe cubrir tanto el "qué hace" como el "cómo se comporta".

Autoevaluación:Si hoy fuera el lanzamiento oficial, ¿qué prueba no funcional les quita el

sueño?

Tarea/Próximo paso: Subir el informe al Canvas y preparar los ajustes en el código para

el APF2 de la Semana 9.

CIERRE

