const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat
} = require("docx");

const border = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };
const fullWidth = 9360;

function labelCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    shading: { fill: "E8EDF2", type: ShadingType.CLEAR },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ children: [new TextRun({ text, bold: true, font: "Arial", size: 20 })] })]
  });
}
function valueCell(text, width) {
  return new TableCell({
    borders, width: { size: width, type: WidthType.DXA },
    margins: cellMargins,
    verticalAlign: "center",
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20 })] })]
  });
}
function row2(label, value, lw = 3120, vw = 6240) {
  return new TableRow({ children: [labelCell(label, lw), valueCell(value, vw)] });
}
function sectionTitle(text) {
  return new Paragraph({
    spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 26, color: "1F3864" })]
  });
}
function subTitle(text) {
  return new Paragraph({
    spacing: { before: 200, after: 120 },
    children: [new TextRun({ text, bold: true, font: "Arial", size: 22, color: "2E75B6" })]
  });
}
function bodyText(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 20 })]
  });
}
function italicText(text) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [new TextRun({ text, italics: true, font: "Arial", size: 20, color: "555555" })]
  });
}
function emptyRow() {
  return new Paragraph({ spacing: { before: 40, after: 40 }, children: [] });
}
function boldText(label, value) {
  return new Paragraph({
    spacing: { before: 60, after: 60 },
    children: [
      new TextRun({ text: label, bold: true, font: "Arial", size: 20 }),
      new TextRun({ text: value, font: "Arial", size: 20 })
    ]
  });
}
function checkbox(text) {
  return new TextRun({ text: `[ ] ${text}`, font: "Arial", size: 20 });
}

function makeTable(rows, widths) {
  const totalW = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalW, type: WidthType.DXA },
    columnWidths: widths,
    rows: rows.map(cells => new TableRow({
      children: cells.map((c, i) => {
        const isLabel = i === 0;
        return new TableCell({
          borders,
          width: { size: widths[i], type: WidthType.DXA },
          shading: isLabel ? { fill: "E8EDF2", type: ShadingType.CLEAR } : undefined,
          margins: cellMargins,
          verticalAlign: "center",
          children: [new Paragraph({ children: [new TextRun({
            text: c, bold: isLabel, font: "Arial", size: 20
          })] })]
        });
      })
    }))
  });
}

const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F3864" },
        paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Arial", color: "2E75B6" },
        paragraph: { spacing: { before: 300, after: 200 }, outlineLevel: 1 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1200, bottom: 1440, left: 1200 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "SS-UTP-2025 | Versión 1.0", font: "Arial", size: 16, color: "888888", italics: true })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "Facultad de Ingeniería — Universidad Tecnológica del Perú | Pág. ", font: "Arial", size: 16, color: "888888" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 16, color: "888888" }),
          ]
        })]
      })
    },
    children: [
      // TITLE
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 100 },
        children: [new TextRun({ text: "FORMATO DE SOLICITUD DE SERVICIO", bold: true, font: "Arial", size: 32, color: "1F3864" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [new TextRun({ text: "Gestión de Solicitudes de Información y Acceso", font: "Arial", size: 22, color: "2E75B6" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 60 },
        children: [new TextRun({ text: "Facultad de Ingeniería | Semana 10", font: "Arial", size: 20, color: "555555" })]
      }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { after: 200 },
        children: [new TextRun({ text: "Código: SS-UTP-2025 | Versión: 1.0 | Revisión: 001", italics: true, font: "Arial", size: 18, color: "888888" })]
      }),

      // INSTRUCTIONS
      new Paragraph({
        spacing: { before: 200, after: 120 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "1F3864", space: 4 } },
        children: [new TextRun({ text: "INSTRUCCIONES PARA EL EQUIPO", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      bodyText("Este formato está dise\u00F1ado para documentar formalmente las solicitudes de servicio seg\u00FAn los lineamientos de ITIL 4."),
      bodyText("Recuerda que una solicitud de servicio NO es un incidente."),
      bodyText("Las solicitudes son peticiones planificadas y anticipadas para obtener informaci\u00F3n, acceso u otros recursos del Cat\u00E1logo de Servicios."),
      bodyText("Complete todos los campos con informaci\u00F3n real y coherente."),
      bodyText("Si un campo no aplica a su caso, escriba \u201CN/A\u201D y justifique brevemente."),
      bodyText("El formato debe estar firmado por todos los aprobadores requeridos antes de ser entregado."),

      // SECTION 1
      new Paragraph({ children: [new PageBreak()] }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 1 | IDENTIFICACI\u00D3N DE LA SOLICITUD", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      makeTable([
        ["N.\u00B0 de Solicitud:", "SS-2025-001"],
        ["Fecha de Solicitud:", "15 / 05 / 2025"],
        ["Hora de Registro:", "10:30 (formato 24 h)"],
        ["Canal de Solicitud:", "Portal Web"],
        ["Nombre del Proyecto:", "EduSync AI \u2014 Sistema de Gesti\u00F3n Integral para Centros de Terapia"],
        ["C\u00F3digo del Proyecto:", "MOS-2025-UTP"],
      ], [3120, 6240]),

      // SECTION 2
      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 2 | DATOS DEL SOLICITANTE", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      makeTable([
        ["Nombre Completo:", "Quispe Mamani, Alberto Rafael"],
        ["C\u00F3digo de Estudiante:", "U20241834"],
        ["Correo Institucional:", "alberto.quispe@utp.edu.pe"],
        ["Ciclo / Secci\u00F3n:", "2025-1 / Secci\u00F3n B"],
        ["Tel\u00E9fono de Contacto:", "+51 987 654 321"],
        ["Rol en el Proyecto:", "L\u00EDder de Proyecto"],
        ["Nombre del Docente:", "Mg. Ing. Carlos Mendoza L\u00F3pez"],
      ], [3120, 6240]),

      // SECTION 3
      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 3 | CLASIFICACI\u00D3N DE LA SOLICITUD", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      italicText("La correcta clasificaci\u00F3n determina el flujo de atenci\u00F3n y los aprobadores requeridos. Seg\u00FAn ITIL 4, una solicitud de servicio es una petici\u00F3n formal para que se provea algo que forma parte de la entrega normal del servicio."),
      emptyRow(),
      boldText("Tipo de Solicitud: ", "De Informaci\u00F3n y De Acceso"),
      boldText("Subcategor\u00EDa: ", ""),
      bodyText("  De INFORMACI\u00D3N: Solicitud de manuales o documentaci\u00F3n t\u00E9cnica"),
      bodyText("  De ACCESO: Nuevo acceso a sistema o m\u00F3dulo"),
      boldText("Prioridad: ", "Alta"),

      // SECTION 4
      new Paragraph({ children: [new PageBreak()] }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 4 | DESCRIPCI\u00D3N DETALLADA DE LA SOLICITUD", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      italicText("N\u00FAcleo del formato. Proporcione informaci\u00F3n detallada para que el equipo comprenda qu\u00E9 se necesita, por qu\u00E9 y las condiciones esperadas de entrega."),

      subTitle("4.1 Descripci\u00F3n de la Solicitud"),
      bodyText("Se solicita acceso al m\u00F3dulo de configuraci\u00F3n del sistema EduSync AI y la documentaci\u00F3n t\u00E9cnica de la API REST para la integraci\u00F3n del m\u00F3dulo de juegos terap\u00E9uticos con clasificador SVM. El acceso requerido incluye:"),
      bodyText("\u2022 Credenciales de administrador para el entorno de pruebas (staging)"),
      bodyText("\u2022 Documentaci\u00F3n de endpoints REST del blueprint /api/games/*"),
      bodyText("\u2022 Acceso a la base de datos MySQL para consultar SessionMetrics y Game"),
      bodyText("\u2022 Repositorio del modelo SVM entrenado (ai_models/svm_model.pkl)"),

      subTitle("4.2 Justificaci\u00F3n Acad\u00E9mica"),
      bodyText("El equipo se encuentra en el Sprint 4 del cronograma del proyecto (Semanas 7-8), cuya entrega principal es la implementaci\u00F3n del clasificador SVM para ajuste autom\u00E1tico de dificultad de juegos terap\u00E9uticos y la generaci\u00F3n de reportes autom\u00E1ticos. Sin acceso al entorno de pruebas y a la documentaci\u00F3n de la API, no es posible completar la integraci\u00F3n del backend Flask con el frontend Angular 20. El impacto de no atender esta solicitud implica el retraso de la entrega del Sprint 4 y la imposibilidad de realizar las pruebas de integraci\u00F3n del m\u00F3dulo de IA."),

      subTitle("4.3 Usuarios Afectados o Beneficiados"),
      bodyText("2 desarrolladores backend (integraci\u00F3n API Flask + modelo SVM), 1 desarrollador frontend (componentes Angular para visualizaci\u00F3n de m\u00E9tricas), 1 terapeuta (pruebas de usuario del m\u00F3dulo de juegos). Impacto directo: 4 personas. Impacto indirecto: 5 terapeutas + 60-80 pacientes del Centro de Terapias Juan Pablo II."),

      subTitle("4.4 Recursos o Sistemas Involucrados"),
      bodyText("Backend: Flask 2.3 con blueprint api_bp (endpoints /api/games/*, /api/sessions/*). Frontend: Angular 20 SPA (m\u00F3dulo de juegos terap\u00E9uticos). Base de datos: MySQL (tablas User, Appointment, SessionMetrics, Game, AppointmentGame). Modelo ML: Scikit-learn SVM con kernel RBF (ai_models/svm_model.pkl). Infraestructura: Railway.app (producci\u00F3n) + Servidor cPanel (staging). Servicios externos: Groq API, Google Drive API."),

      subTitle("4.5 Fecha Requerida de Atenci\u00F3n"),
      bodyText("22 / 05 / 2025 \u2014 Urgente: El Sprint 4 finaliza la semana del 26/05 y las pruebas de integraci\u00F3n requieren al menos 3 d\u00EDas h\u00E1biles."),

      // SECTION 5
      new Paragraph({ children: [new PageBreak()] }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 5 | DETALLE DE ACCESO", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      italicText("Completar solo si la solicitud es De Acceso."),
      emptyRow(),
      makeTable([
        ["Sistema o Aplicaci\u00F3n:", "EduSync AI \u2014 Panel de Administraci\u00F3n"],
        ["URL / Ruta de Acceso:", "https://staging.moscowle.centrojuanpabloii.com/admin"],
        ["Tipo de Permiso Solicitado:", "Administrador (configuraci\u00F3n de juegos, usuarios, m\u00E9tricas)"],
        ["Nivel de Acceso Requerido:", "M\u00F3dulos: Games (CRUD + SVM), Users (lectura), Reports (generaci\u00F3n), Sessions (visualizaci\u00F3n completa)"],
        ["Due\u00F1o del Sistema:", "Administrador del Centro de Terapias Juan Pablo II"],
        ["Fecha Inicio / Expiraci\u00F3n:", "De: 15/05/2025 Hasta: 30/06/2025"],
      ], [3120, 6240]),

      subTitle("Justificaci\u00F3n de Seguridad"),
      bodyText("El nivel de acceso Administrador es necesario para configurar los par\u00E1metros del clasificador SVM (umbrales de dificultad, pesos del modelo) y para asignar juegos a sesiones de terapia. Medidas de seguridad: autenticaci\u00F3n con bcrypt y tokens JWT (expiraci\u00F3n 8 h), rate limiting (20 req/min), HTTPS forzado (Flask-Talisman), registro de auditor\u00EDa en Sentry, acceso expira el 30/06/2025."),

      // SECTION 6
      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 6 | FLUJO DE APROBACI\u00D3N", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      makeTable([
        ["Aprobador / Rol", "Nombre y Firma", "Fecha", "Decisi\u00F3n"],
        ["Jefe Inmediato / L\u00EDder de Proyecto", "Alberto Quispe Mamani", "15/05/2025", "Aprobado"],
        ["Administrador del Sistema", "[Pendiente]", "[Pendiente]", "[ ] Aprobado / [ ] Rechazado"],
        ["Responsable de TI / Mesa de Ayuda", "[Pendiente]", "[Pendiente]", "[ ] Aprobado / [ ] Rechazado"],
      ], [2800, 2500, 1600, 2460]),

      subTitle("Observaciones del Proceso de Aprobaci\u00F3n"),
      italicText("[En caso de rechazo, indique el motivo y las condiciones para reformular. En caso de aprobaci\u00F3n condicional, especifique restricciones.]"),

      // SECTION 7
      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 7 | ACUERDO DE NIVEL DE SERVICIO (SLA)", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      makeTable([
        ["Prioridad", "Tiempo Estimado", "Estado"],
        ["Alta (afecta operaci\u00F3n cr\u00EDtica)", "4 horas h\u00E1biles", "[ ] Dentro del SLA / [ ] Fuera del SLA"],
        ["Media (impacto moderado)", "1 d\u00EDa h\u00E1bil", "[ ] Dentro del SLA / [ ] Fuera del SLA"],
        ["Baja (mejora o consulta)", "3 d\u00EDas h\u00E1biles", "[ ] Dentro del SLA / [ ] Fuera del SLA"],
      ], [3200, 3000, 3160]),
      emptyRow(),
      boldText("Prioridad Asignada: ", "Alta \u2014 afecta la entrega del Sprint 4 del proyecto acad\u00E9mico"),
      boldText("Responsable de Atenci\u00F3n (TI): ", "[Nombre del integrante encargado]"),
      boldText("Fechas: ", "Inicio: [DD/MM/AAAA] | Real de Cierre: [DD/MM/AAAA]"),

      // SECTION 8
      new Paragraph({ children: [new PageBreak()] }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 8 | REGISTRO DE CUMPLIMIENTO Y CIERRE", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      boldText("Estado Final de la Solicitud: ", "[ ] Atendida / [ ] Parcial / [ ] Rechazada / [ ] Cancelada"),
      subTitle("Detalle de la Soluci\u00F3n Brindada"),
      italicText("[Describa c\u00F3mo se atendi\u00F3 la solicitud: qu\u00E9 se entreg\u00F3, qu\u00E9 permisos se otorgaron, qu\u00E9 informaci\u00F3n se proporcion\u00F3.]"),
      subTitle("Evidencias de Cumplimiento"),
      italicText("[Liste las evidencias: capturas de pantalla, correos, registros del sistema, etc.]"),
      emptyRow(),
      boldText("Calificaci\u00F3n del Servicio: ", "[ ] Excelente / [ ] Bueno / [ ] Regular / [ ] Deficiente"),
      subTitle("Comentarios del Solicitante"),
      italicText("[Observaciones adicionales sobre la calidad y oportunidad del servicio recibido.]"),
      emptyRow(),
      bodyText("Firma del Solicitante: _______________________ (Nombre: _________________ Fecha: _____________)"),
      bodyText("Firma de Resp. TI: _______________________ (Nombre: _________________ Fecha: _____________)"),

      // SECTION 9
      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 9 | REFLEXI\u00D3N DEL EQUIPO (SUSTENTACI\u00D3N ACAD\u00C9MICA)", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),

      subTitle("9.1 \u00BFC\u00F3mo diferencia su equipo una Solicitud de Informaci\u00F3n de una Solicitud de Acceso en el contexto de su proyecto?"),
      bodyText("En el proyecto EduSync AI, una Solicitud de Informaci\u00F3n corresponde a peticiones de documentaci\u00F3n t\u00E9cnica o datos que no implican modificar permisos. Por ejemplo, solicitar el manual de la API REST de juegos terap\u00E9uticos o consultar el esquema de la base de datos. Una Solicitud de Acceso, en cambio, implica otorgar credenciales o permisos para operar sobre el sistema, como crear un usuario administrador para configurar el clasificador SVM. La diferencia clave es el impacto sobre la seguridad: las solicitudes de acceso requieren aprobaci\u00F3n m\u00FAltiple (administrador del sistema + TI), mientras que las de informaci\u00F3n pueden ser resueltas por mesa de ayuda."),

      subTitle("9.2 \u00BFDe qu\u00E9 manera este formato garantiza la seguridad y trazabilidad de la informaci\u00F3n del proyecto?"),
      bodyText("1) Segmentaci\u00F3n de aprobaciones (Secci\u00F3n 6): Tres roles deben aprobar (l\u00EDder, administrador, TI), alineado con ISO 27001 A.9.2.1. 2) Justificaci\u00F3n de seguridad obligatoria (Secci\u00F3n 5): Aplica el principio de m\u00EDnimo privilegio. 3) SLA con priorizaci\u00F3n (Secci\u00F3n 7): Tiempos de atenci\u00F3n diferenciados seg\u00FAn el impacto. 4) Registro de cumplimiento (Secci\u00F3n 8): Documenta qu\u00E9, cu\u00E1ndo y con qu\u00E9 evidencias se entreg\u00F3, creando un registro de auditor\u00EDa completo para trazabilidad ITIL 4."),

      subTitle("9.3 \u00BFQu\u00E9 ajustes realizar\u00EDa al formato para adaptarlo mejor a las caracter\u00EDsticas espec\u00EDficas de su proyecto?"),
      bodyText("Ajuste 1 \u2014 Niveles de acceso por m\u00F3dulo granular: EduSync AI tiene 12 blueprints con permisos por rol (admin, terapista, jugador). Se agregar\u00EDa una tabla donde cada m\u00F3dulo tenga su propio nivel de acceso solicitado, similar al Anexo C del documento del proyecto."),
      bodyText("Ajuste 2 \u2014 Integraci\u00F3n con el motor de flujo de trabajo inteligente: El sistema incluye un workflow_engine que genera acciones inteligentes. Se podr\u00EDa indicar si la solicitud fue generada autom\u00E1ticamente por el motor o es manual."),
      bodyText("Ajuste 3 \u2014 Campo para recursos cloud y APIs externas: EduSync AI se integra con Groq, Gemini, Google Drive y Gmail SMTP. Se agregar\u00EDa una subsecci\u00F3n para tokens de API y credenciales OAuth2, siguiendo ISO 27001 A.9.4.2."),

      // SECTION 10
      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        spacing: { before: 200, after: 160 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 4 } },
        children: [new TextRun({ text: "SECCI\u00D3N 10 | HISTORIAL DE VERSIONES DEL FORMATO", bold: true, font: "Arial", size: 24, color: "1F3864" })]
      }),
      makeTable([
        ["Ver.", "Fecha", "Descripci\u00F3n del Cambio", "Elaborado por"],
        ["1.0", "2025", "Versi\u00F3n inicial del formato \u2014 Semana 10, Sesi\u00F3n 1", "Docente del Curso"],
        ["1.1", "15/05/2025", "Completado con datos del proyecto EduSync AI \u2014 Centro de Terapias Juan Pablo II", "Alberto Quispe Mamani \u2014 L\u00EDder de Proyecto"],
      ], [800, 1400, 4800, 2360]),

      new Paragraph({ spacing: { before: 360 } }),
      new Paragraph({
        alignment: AlignmentType.CENTER,
        spacing: { before: 200, after: 100 },
        children: [new TextRun({ text: "Gesti\u00F3n de Servicios de TI \u2014 Facultad de Ingenier\u00EDa | Universidad Tecnol\u00F3gica del Per\u00FA | 2025", italics: true, font: "Arial", size: 18, color: "888888" })]
      }),
    ]
  }]
});

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("Formato_Solicitud_Servicio_Completado.docx", buffer);
  console.log("✅ DOCX generado: Formato_Solicitud_Servicio_Completado.docx");
});
