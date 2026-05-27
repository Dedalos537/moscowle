from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, black, grey
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable
)
from reportlab.lib import colors

def build_pdf():
    doc = SimpleDocTemplate(
        "Formato_Solicitud_Servicio_Completado.pdf",
        pagesize=letter,
        topMargin=0.75*inch,
        bottomMargin=0.75*inch,
        leftMargin=0.75*inch,
        rightMargin=0.75*inch
    )

    styles = getSampleStyleSheet()
    navy = HexColor("#1F3864")
    blue = HexColor("#2E75B6")
    grey_c = HexColor("#555555")
    light_grey = HexColor("#E8EDF2")

    s_title = ParagraphStyle("CustomTitle", parent=styles["Title"],
        fontSize=18, leading=22, textColor=navy, spaceAfter=6, alignment=TA_CENTER,
        fontName="Helvetica-Bold")
    s_subtitle = ParagraphStyle("CustomSubtitle", parent=styles["Normal"],
        fontSize=12, leading=15, textColor=blue, spaceAfter=4, alignment=TA_CENTER)
    s_code = ParagraphStyle("Code", parent=styles["Normal"],
        fontSize=9, leading=11, textColor=grey_c, spaceAfter=16, alignment=TA_CENTER)
    s_section = ParagraphStyle("Section", parent=styles["Heading2"],
        fontSize=14, leading=17, textColor=navy, spaceBefore=18, spaceAfter=10,
        fontName="Helvetica-Bold")
    s_sub = ParagraphStyle("SubSection", parent=styles["Heading3"],
        fontSize=11, leading=14, textColor=blue, spaceBefore=12, spaceAfter=6,
        fontName="Helvetica-Bold")
    s_body = ParagraphStyle("Body", parent=styles["Normal"],
        fontSize=9.5, leading=13, spaceBefore=3, spaceAfter=3, alignment=TA_JUSTIFY)
    s_italic = ParagraphStyle("Italic", parent=styles["Normal"],
        fontSize=9.5, leading=13, textColor=grey_c, spaceBefore=3, spaceAfter=3,
        alignment=TA_LEFT, fontName="Helvetica-Oblique")
    s_bold = ParagraphStyle("BoldBody", parent=styles["Normal"],
        fontSize=9.5, leading=13, spaceBefore=3, spaceAfter=3, fontName="Helvetica-Bold")
    s_footer = ParagraphStyle("FooterStyle", parent=styles["Normal"],
        fontSize=8, leading=10, textColor=grey_c, alignment=TA_CENTER, spaceBefore=20)

    def make_table(data, col_widths):
        t = Table(data, colWidths=col_widths)
        style_cmds = [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEADING", (0, 0), (-1, -1), 12),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#999999")),
        ]
        for i, row in enumerate(data):
            if i == 0:
                style_cmds.append(("FONTNAME", (0, i), (-1, i), "Helvetica-Bold"))
                style_cmds.append(("BACKGROUND", (0, i), (-1, i), light_grey))
            else:
                style_cmds.append(("BACKGROUND", (0, i), (0, i), light_grey))
                style_cmds.append(("FONTNAME", (0, i), (0, i), "Helvetica-Bold"))
        t.setStyle(TableStyle(style_cmds))
        return t

    def section_hr():
        return HRFlowable(width="100%", thickness=1.5, color=blue, spaceAfter=8)

    story = []

    # TITLE
    story.append(Paragraph("FORMATO DE SOLICITUD DE SERVICIO", s_title))
    story.append(Paragraph("Gesti\u00f3n de Solicitudes de Informaci\u00f3n y Acceso", s_subtitle))
    story.append(Paragraph("Facultad de Ingenier\u00eda | Semana 10", s_subtitle))
    story.append(Paragraph(
        "C\u00f3digo: SS-UTP-2025 | Versi\u00f3n: 1.0 | Revisi\u00f3n: 001", s_code))
    story.append(section_hr())

    # INSTRUCTIONS
    story.append(Paragraph("INSTRUCCIONES PARA EL EQUIPO", s_section))
    story.append(Paragraph(
        "Este formato est\u00e1 dise\u00f1ado para documentar formalmente las solicitudes de servicio "
        "seg\u00fan los lineamientos de ITIL 4.", s_body))
    story.append(Paragraph(
        "Recuerda que una solicitud de servicio NO es un incidente. Las solicitudes son peticiones "
        "planificadas y anticipadas para obtener informaci\u00f3n, acceso u otros recursos del "
        "Cat\u00e1logo de Servicios.", s_body))
    story.append(Paragraph(
        "Complete todos los campos con informaci\u00f3n real y coherente. Si un campo no aplica a su "
        "caso, escriba \"N/A\" y justifique brevemente. El formato debe estar firmado por todos los "
        "aprobadores requeridos antes de ser entregado.", s_body))

    # SECTION 1
    story.append(Paragraph("SECCI\u00d3N 1 | IDENTIFICACI\u00d3N DE LA SOLICITUD", s_section))
    story.append(make_table([
        ["N.\u00b0 de Solicitud:", "SS-2025-001"],
        ["Fecha de Solicitud:", "15 / 05 / 2025"],
        ["Hora de Registro:", "10:30 (formato 24 h)"],
        ["Canal de Solicitud:", "Portal Web"],
        ["Nombre del Proyecto:", "EduSync AI \u2014 Sistema de Gesti\u00f3n Integral para Centros de Terapia"],
        ["C\u00f3digo del Proyecto:", "MOS-2025-UTP"],
    ], [2.2*inch, 3.8*inch]))

    # SECTION 2
    story.append(Paragraph("SECCI\u00d3N 2 | DATOS DEL SOLICITANTE", s_section))
    story.append(make_table([
        ["Nombre Completo:", "Quispe Mamani, Alberto Rafael"],
        ["C\u00f3digo de Estudiante:", "U20241834"],
        ["Correo Institucional:", "alberto.quispe@utp.edu.pe"],
        ["Ciclo / Secci\u00f3n:", "2025-1 / Secci\u00f3n B"],
        ["Tel\u00e9fono de Contacto:", "+51 987 654 321"],
        ["Rol en el Proyecto:", "L\u00edder de Proyecto"],
        ["Nombre del Docente:", "Mg. Ing. Carlos Mendoza L\u00f3pez"],
    ], [2.2*inch, 3.8*inch]))

    # SECTION 3
    story.append(Paragraph("SECCI\u00d3N 3 | CLASIFICACI\u00d3N DE LA SOLICITUD", s_section))
    story.append(Paragraph(
        "La correcta clasificaci\u00f3n determina el flujo de atenci\u00f3n y los aprobadores requeridos. "
        "Seg\u00fan ITIL 4, una solicitud de servicio es una petici\u00f3n formal para que se provea algo "
        "que forma parte de la entrega normal del servicio.", s_italic))
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>Tipo de Solicitud:</b> De Informaci\u00f3n y De Acceso", s_body))
    story.append(Paragraph("<b>Subcategor\u00eda:</b>", s_body))
    story.append(Paragraph(
        "&nbsp;&nbsp;De INFORMACI\u00d3N: Solicitud de manuales o documentaci\u00f3n t\u00e9cnica", s_body))
    story.append(Paragraph(
        "&nbsp;&nbsp;De ACCESO: Nuevo acceso a sistema o m\u00f3dulo", s_body))
    story.append(Paragraph("<b>Prioridad:</b> Alta", s_body))

    # SECTION 4
    story.append(PageBreak())
    story.append(Paragraph("SECCI\u00d3N 4 | DESCRIPCI\u00d3N DETALLADA DE LA SOLICITUD", s_section))
    story.append(Paragraph(
        "N\u00facleo del formato. Proporcione informaci\u00f3n detallada para que el equipo "
        "comprenda qu\u00e9 se necesita, por qu\u00e9 y las condiciones esperadas de entrega.", s_italic))

    story.append(Paragraph("4.1 Descripci\u00f3n de la Solicitud", s_sub))
    story.append(Paragraph(
        "Se solicita acceso al m\u00f3dulo de configuraci\u00f3n del sistema EduSync AI y la "
        "documentaci\u00f3n t\u00e9cnica de la API REST para la integraci\u00f3n del m\u00f3dulo de juegos "
        "terap\u00e9uticos con clasificador SVM. El acceso requerido incluye:", s_body))
    story.append(Paragraph(
        "\u2022 Credenciales de administrador para el entorno de pruebas (staging)", s_body))
    story.append(Paragraph(
        "\u2022 Documentaci\u00f3n de endpoints REST del blueprint /api/games/*", s_body))
    story.append(Paragraph(
        "\u2022 Acceso a la base de datos MySQL para consultar SessionMetrics y Game", s_body))
    story.append(Paragraph(
        "\u2022 Repositorio del modelo SVM entrenado (ai_models/svm_model.pkl)", s_body))

    story.append(Paragraph("4.2 Justificaci\u00f3n Acad\u00e9mica", s_sub))
    story.append(Paragraph(
        "El equipo se encuentra en el Sprint 4 del cronograma del proyecto (Semanas 7-8), cuya "
        "entrega principal es la implementaci\u00f3n del clasificador SVM para ajuste autom\u00e1tico de "
        "dificultad de juegos terap\u00e9uticos y la generaci\u00f3n de reportes autom\u00e1ticos. Sin acceso "
        "al entorno de pruebas y a la documentaci\u00f3n de la API, no es posible completar la "
        "integraci\u00f3n del backend Flask con el frontend Angular 20. El impacto de no atender esta "
        "solicitud implica el retraso de la entrega del Sprint 4 y la imposibilidad de realizar "
        "las pruebas de integraci\u00f3n del m\u00f3dulo de IA.", s_body))

    story.append(Paragraph("4.3 Usuarios Afectados o Beneficiados", s_sub))
    story.append(Paragraph(
        "2 desarrolladores backend (integraci\u00f3n API Flask + modelo SVM), 1 desarrollador frontend "
        "(componentes Angular para visualizaci\u00f3n de m\u00e9tricas), 1 terapeuta (pruebas de usuario "
        "del m\u00f3dulo de juegos). Impacto directo: 4 personas. Impacto indirecto: 5 terapeutas + "
        "60-80 pacientes del Centro de Terapias Juan Pablo II.", s_body))

    story.append(Paragraph("4.4 Recursos o Sistemas Involucrados", s_sub))
    story.append(Paragraph(
        "Backend: Flask 2.3 con blueprint api_bp (endpoints /api/games/*, /api/sessions/*). "
        "Frontend: Angular 20 SPA (m\u00f3dulo de juegos terap\u00e9uticos). Base de datos: MySQL "
        "(tablas User, Appointment, SessionMetrics, Game, AppointmentGame). Modelo ML: "
        "Scikit-learn SVM con kernel RBF (ai_models/svm_model.pkl). Infraestructura: "
        "Railway.app (producci\u00f3n) + Servidor cPanel (staging). Servicios externos: Groq API, "
        "Google Drive API.", s_body))

    story.append(Paragraph("4.5 Fecha Requerida de Atenci\u00f3n", s_sub))
    story.append(Paragraph(
        "22 / 05 / 2025 \u2014 Urgente: El Sprint 4 finaliza la semana del 26/05 y las pruebas de "
        "integraci\u00f3n requieren al menos 3 d\u00edas h\u00e1biles.", s_body))

    # SECTION 5
    story.append(PageBreak())
    story.append(Paragraph("SECCI\u00d3N 5 | DETALLE DE ACCESO", s_section))
    story.append(Paragraph(
        "Completar solo si la solicitud es De Acceso.", s_italic))
    story.append(Spacer(1, 6))
    story.append(make_table([
        ["Sistema o Aplicaci\u00f3n:", "EduSync AI \u2014 Panel de Administraci\u00f3n"],
        ["URL / Ruta de Acceso:", "https://staging.moscowle.centrojuanpabloii.com/admin"],
        ["Tipo de Permiso Solicitado:", "Administrador (configuraci\u00f3n de juegos, usuarios, m\u00e9tricas)"],
        ["Nivel de Acceso Requerido:", "M\u00f3dulos: Games (CRUD + SVM), Users (lectura), Reports, Sessions"],
        ["Due\u00f1o del Sistema:", "Administrador del Centro de Terapias Juan Pablo II"],
        ["Fecha Inicio / Expiraci\u00f3n:", "De: 15/05/2025 Hasta: 30/06/2025"],
    ], [2.2*inch, 3.8*inch]))

    story.append(Paragraph("Justificaci\u00f3n de Seguridad", s_sub))
    story.append(Paragraph(
        "El nivel de acceso Administrador es necesario para configurar los par\u00e1metros del "
        "clasificador SVM (umbrales de dificultad, pesos del modelo) y para asignar juegos a "
        "sesiones de terapia. Medidas de seguridad: autenticaci\u00f3n con bcrypt y tokens JWT "
        "(expiraci\u00f3n 8 h), rate limiting (20 req/min), HTTPS forzado (Flask-Talisman), "
        "registro de auditor\u00eda en Sentry, acceso expira el 30/06/2025.", s_body))

    # SECTION 6
    story.append(Paragraph("SECCI\u00d3N 6 | FLUJO DE APROBACI\u00d3N", s_section))
    story.append(make_table([
        ["Aprobador / Rol", "Nombre y Firma", "Fecha", "Decisi\u00f3n"],
        ["Jefe / L\u00edder de Proyecto", "Alberto Quispe M.", "15/05/2025", "Aprobado"],
        ["Administrador del Sistema", "[Pendiente]", "[Pendiente]", "[ ] Aprob / [ ] Rech"],
        ["Resp. TI / Mesa de Ayuda", "[Pendiente]", "[Pendiente]", "[ ] Aprob / [ ] Rech"],
    ], [1.8*inch, 1.8*inch, 1.1*inch, 1.3*inch]))

    story.append(Paragraph(
        "Observaciones del Proceso de Aprobaci\u00f3n:", s_sub))
    story.append(Paragraph(
        "[En caso de rechazo, indique motivo y condiciones para reformular. "
        "En caso de aprobaci\u00f3n condicional, especifique restricciones.]", s_italic))

    # SECTION 7
    story.append(Paragraph("SECCI\u00d3N 7 | ACUERDO DE NIVEL DE SERVICIO (SLA)", s_section))
    story.append(make_table([
        ["Prioridad", "Tiempo Estimado", "Estado"],
        ["Alta (afecta operaci\u00f3n cr\u00edtica)", "4 horas h\u00e1biles", "[ ] SLA / [ ] Fuera"],
        ["Media (impacto moderado)", "1 d\u00eda h\u00e1bil", "[ ] SLA / [ ] Fuera"],
        ["Baja (mejora o consulta)", "3 d\u00edas h\u00e1biles", "[ ] SLA / [ ] Fuera"],
    ], [2.2*inch, 1.8*inch, 2.0*inch]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<b>Prioridad Asignada:</b> Alta \u2014 afecta la entrega del Sprint 4 del proyecto acad\u00e9mico",
        s_body))
    story.append(Paragraph(
        "<b>Responsable de Atenci\u00f3n (TI):</b> [Nombre del integrante encargado]", s_body))
    story.append(Paragraph(
        "<b>Fechas:</b> Inicio: [DD/MM/AAAA] | Real de Cierre: [DD/MM/AAAA]", s_body))

    # SECTION 8
    story.append(PageBreak())
    story.append(Paragraph("SECCI\u00d3N 8 | REGISTRO DE CUMPLIMIENTO Y CIERRE", s_section))
    story.append(Paragraph(
        "<b>Estado Final de la Solicitud:</b> [ ] Atendida / [ ] Parcial / [ ] Rechazada / [ ] Cancelada",
        s_body))
    story.append(Paragraph("Detalle de la Soluci\u00f3n Brindada", s_sub))
    story.append(Paragraph(
        "[Describa c\u00f3mo se atendi\u00f3 la solicitud: qu\u00e9 se entreg\u00f3, qu\u00e9 permisos se "
        "otorgaron, qu\u00e9 informaci\u00f3n se proporcion\u00f3.]", s_italic))
    story.append(Paragraph("Evidencias de Cumplimiento", s_sub))
    story.append(Paragraph(
        "[Liste las evidencias: capturas de pantalla, correos, registros del sistema, etc.]", s_italic))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "<b>Calificaci\u00f3n del Servicio:</b> [ ] Excelente / [ ] Bueno / [ ] Regular / [ ] Deficiente",
        s_body))
    story.append(Paragraph("Comentarios del Solicitante", s_sub))
    story.append(Paragraph(
        "[Observaciones adicionales sobre la calidad y oportunidad del servicio recibido.]", s_italic))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "Firma del Solicitante: _______________________ "
        "(Nombre: _________________ Fecha: _____________)", s_body))
    story.append(Paragraph(
        "Firma de Resp. TI: _______________________ "
        "(Nombre: _________________ Fecha: _____________)", s_body))

    # SECTION 9
    story.append(Paragraph(
        "SECCI\u00d3N 9 | REFLEXI\u00d3N DEL EQUIPO (SUSTENTACI\u00d3N ACAD\u00c9MICA)", s_section))

    story.append(Paragraph(
        "9.1 \u00bfC\u00f3mo diferencia su equipo una Solicitud de Informaci\u00f3n de una "
        "Solicitud de Acceso en el contexto de su proyecto?", s_sub))
    story.append(Paragraph(
        "En el proyecto EduSync AI, una Solicitud de Informaci\u00f3n corresponde a peticiones de "
        "documentaci\u00f3n t\u00e9cnica o datos que no implican modificar permisos. Por ejemplo, "
        "solicitar el manual de la API REST de juegos terap\u00e9uticos o consultar el esquema de "
        "la base de datos. Una Solicitud de Acceso implica otorgar credenciales o permisos para "
        "operar sobre el sistema, como crear un usuario administrador para configurar el clasificador "
        "SVM. La diferencia clave es el impacto sobre la seguridad: las solicitudes de acceso "
        "requieren aprobaci\u00f3n m\u00faltiple (administrador del sistema + TI), mientras que las de "
        "informaci\u00f3n pueden ser resueltas por mesa de ayuda.", s_body))

    story.append(Paragraph(
        "9.2 \u00bfDe qu\u00e9 manera este formato garantiza la seguridad y trazabilidad de la "
        "informaci\u00f3n del proyecto?", s_sub))
    story.append(Paragraph(
        "1) Segmentaci\u00f3n de aprobaciones (Secci\u00f3n 6): Tres roles deben aprobar "
        "(l\u00edder, administrador, TI), alineado con ISO 27001 A.9.2.1. 2) Justificaci\u00f3n de "
        "seguridad obligatoria (Secci\u00f3n 5): Aplica el principio de m\u00ednimo privilegio. "
        "3) SLA con priorizaci\u00f3n (Secci\u00f3n 7): Tiempos de atenci\u00f3n diferenciados seg\u00fan "
        "el impacto. 4) Registro de cumplimiento (Secci\u00f3n 8): Documenta qu\u00e9, cu\u00e1ndo y "
        "con qu\u00e9 evidencias se entreg\u00f3, creando un registro de auditor\u00eda completo para "
        "trazabilidad ITIL 4.", s_body))

    story.append(Paragraph(
        "9.3 \u00bfQu\u00e9 ajustes realizar\u00eda al formato para adaptarlo mejor a las "
        "caracter\u00edsticas espec\u00edficas de su proyecto?", s_sub))
    story.append(Paragraph(
        "<b>Ajuste 1</b> \u2014 Niveles de acceso por m\u00f3dulo granular: EduSync AI tiene 12 "
        "blueprints con permisos por rol (admin, terapista, jugador). Se agregar\u00eda una tabla "
        "donde cada m\u00f3dulo tenga su propio nivel de acceso solicitado, similar al Anexo C del "
        "documento del proyecto.", s_body))
    story.append(Paragraph(
        "<b>Ajuste 2</b> \u2014 Integraci\u00f3n con el motor de flujo de trabajo inteligente: "
        "El sistema incluye un workflow_engine que genera acciones inteligentes. Se podr\u00eda "
        "indicar si la solicitud fue generada autom\u00e1ticamente por el motor o es manual.", s_body))
    story.append(Paragraph(
        "<b>Ajuste 3</b> \u2014 Campo para recursos cloud y APIs externas: EduSync AI se integra "
        "con Groq, Gemini, Google Drive y Gmail SMTP. Se agregar\u00eda una subsecci\u00f3n para "
        "tokens de API y credenciales OAuth2, siguiendo ISO 27001 A.9.4.2.", s_body))

    # SECTION 10
    story.append(Paragraph(
        "SECCI\u00d3N 10 | HISTORIAL DE VERSIONES DEL FORMATO", s_section))
    story.append(make_table([
        ["Ver.", "Fecha", "Descripci\u00f3n del Cambio", "Elaborado por"],
        ["1.0", "2025", "Versi\u00f3n inicial \u2014 Semana 10, Sesi\u00f3n 1", "Docente del Curso"],
        ["1.1", "15/05/2025",
         "Completado con datos del proyecto EduSync AI",
         "Alberto Quispe Mamani"],
    ], [0.6*inch, 1.0*inch, 3.2*inch, 1.2*inch]))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=grey_c, spaceAfter=6))
    story.append(Paragraph(
        "Gesti\u00f3n de Servicios de TI \u2014 Facultad de Ingenier\u00eda | "
        "Universidad Tecnol\u00f3gica del Per\u00fa | 2025", s_footer))

    doc.build(story)
    print("✅ PDF generado: Formato_Solicitud_Servicio_Completado.pdf")

if __name__ == "__main__":
    build_pdf()
