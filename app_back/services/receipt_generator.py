import os
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from flask import current_app
from datetime import datetime

def generate_receipt_pdf(payment, patient):
    """
    Generates a PDF receipt for a given payment.
    Returns: BytesIO object containing the PDF data
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=30
    )
    
    # Contenedor de elementos del PDF
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    styles.add(ParagraphStyle(
        name='ReceiptTitle',
        parent=styles['Heading1'],
        alignment=1,
        fontSize=16,
        spaceAfter=20,
        textColor=colors.HexColor('#65a30d') # Similar a nuestro indigo-800
    ))
    styles.add(ParagraphStyle(
        name='NormalSmall',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray
    ))

    # --- 1. CABECERA ---
    # Intentar cargar logo si existe, si no, solo texto
    logo_path = ''
    try:
        logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = Image(logo_path, width=1.5*inch, height=1.5*inch)
            img.hAlign = 'CENTER'
            elements.append(img)
        else:
            # Simular Logo
            elements.append(Paragraph("<font size=20 color='#86c246'><b>CENTRO DE TERAPIAS</b></font>", styles['Center']))
            elements.append(Paragraph("<font size=16 color='#86c246'><b>JUAN PABLO II</b></font>", styles['Center']))
            elements.append(Spacer(1, 10))
    except Exception as e:
        pass

    if not os.path.exists(logo_path):
        pass # Titulo ya agregado en el else de arriba
    else:
        elements.append(Paragraph("CENTRO DE TERAPIAS JUAN PABLO II", styles['ReceiptTitle']))
        
    elements.append(Paragraph("RUC: 10740365512", styles['Center']))
    elements.append(Paragraph("Jr.Vicus 311, Piura", styles['Center']))
    elements.append(Spacer(1, 20))
    
    # --- 2. TÍTULO DEL RECIBO ---
    receipt_id = f"REC-{payment.id:06d}"
    elements.append(Paragraph(f"RECIBO DE PAGO ELECTRÓNICO N° {receipt_id}", styles['ReceiptTitle']))
    elements.append(Spacer(1, 10))

    # --- 3. DATOS DEL CLIENTE ---
    client_name = patient.guardian_name or patient.username
    client_doc = patient.document_number or patient.id
    
    client_data = [
        [Paragraph('<b>DATOS DEL CLIENTE:</b>', styles['Normal'])],
        ['Nombre/Apoderado:', client_name],
        ['DNI/Documento:', client_doc],
        ['Paciente Asignado:', patient.username]
    ]
    t_client = Table(client_data, colWidths=[2*inch, 4*inch])
    t_client.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f3f4f6')),
        ('SPAN', (0,0), (1,0)),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_client)
    elements.append(Spacer(1, 20))

    # --- 4. DATOS DEL PAGO ---
    date_str = payment.date.strftime("%d/%m/%Y %H:%M")
    
    concept_str = payment.notes if payment.notes else "Servicios de Terapia"
    method_str = str(payment.method).upper()

    payment_data = [
        ['Fecha de Emisión:', date_str],
        ['Método de Pago:', method_str],
        ['Referencia:', payment.reference or '-'],
        ['Concepto:', concept_str]
    ]
    t_payment = Table(payment_data, colWidths=[2*inch, 4*inch])
    t_payment.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_payment)
    elements.append(Spacer(1, 20))

    # --- 5. TOTALES ---
    amount_str = f"S/ {payment.amount:.2f}"
    total_data = [
        ['', 'Subtotal:', amount_str],
        ['', 'TOTAL PAGADO:', amount_str]
    ]
    t_total = Table(total_data, colWidths=[3.5*inch, 1.5*inch, 1*inch])
    t_total.setStyle(TableStyle([
        ('FONT', (1,1), (2,1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (1,1), (2,1), colors.HexColor('#65a30d')),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('LINEABOVE', (1,1), (2,1), 1, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_total)
    elements.append(Spacer(1, 40))

    # --- 6. PIE DE PÁGINA ---
    elements.append(Paragraph("Este documento es un comprobante de control interno.", styles['Center']))
    elements.append(Paragraph("¡Gracias por confiar en el Centro de Terapias Juan Pablo II!", styles['Center']))
    
    # Generar
    doc.build(elements)
    buffer.seek(0)
    return buffer
