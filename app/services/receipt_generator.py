import os
from io import BytesIO

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_receipt_pdf(payment, patient, installment=None, contract=None):
    """
    Generates a PDF receipt for a given payment.
    Optionally includes installment/contract data.
    Returns: BytesIO object containing the PDF data
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)

    elements = []
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(name='Center', alignment=1))
    styles.add(ParagraphStyle(name='Right', alignment=2))
    styles.add(
        ParagraphStyle(
            name='ReceiptTitle',
            parent=styles['Heading1'],
            alignment=1,
            fontSize=16,
            spaceAfter=20,
            textColor=colors.HexColor('#65a30d'),
        )
    )
    styles.add(ParagraphStyle(name='NormalSmall', parent=styles['Normal'], fontSize=9, textColor=colors.grey))

    logo_loaded = False
    try:
        logo_path = os.path.join(current_app.root_path, 'static', 'img', 'logo.png')
        if os.path.exists(logo_path):
            img = Image(logo_path, width=1.5 * inch, height=1.5 * inch)
            img.hAlign = 'CENTER'
            elements.append(img)
            logo_loaded = True
        else:
            elements.append(
                Paragraph("<font size=20 color='#86c246'><b>CENTRO DE TERAPIAS</b></font>", styles['Center'])
            )
            elements.append(Paragraph("<font size=16 color='#86c246'><b>JUAN PABLO II</b></font>", styles['Center']))
            elements.append(Spacer(1, 10))
            logo_loaded = True
    except Exception:
        import traceback
        traceback.print_exc()

    if logo_loaded:
        elements.append(Paragraph('CENTRO DE TERAPIAS JUAN PABLO II', styles['ReceiptTitle']))

    elements.append(Paragraph('RUC: 10740365512', styles['Center']))
    elements.append(Paragraph('Jr.Vicus 311, Piura', styles['Center']))
    elements.append(Spacer(1, 20))

    receipt_id = f'REC-{payment.id:06d}'
    elements.append(Paragraph(f'RECIBO DE PAGO ELECTRÓNICO N° {receipt_id}', styles['ReceiptTitle']))
    elements.append(Spacer(1, 10))

    client_name = patient.guardian_name or patient.username
    client_doc = patient.document_number or patient.id
    guardian_dni = patient.guardian_dni or ''

    client_data = [
        [Paragraph('<b>DATOS DEL CLIENTE:</b>', styles['Normal'])],
        ['Nombre/Apoderado:', client_name],
        ['DNI Apoderado:', guardian_dni],
        ['DNI Paciente:', str(client_doc)],
        ['Paciente Asignado:', patient.username],
    ]
    t_client = Table(client_data, colWidths=[2 * inch, 4 * inch])
    t_client.setStyle(
        TableStyle(
            [
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                ('SPAN', (0, 0), (1, 0)),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t_client)
    elements.append(Spacer(1, 20))

    if contract and installment:
        contract_data = [
            [Paragraph('<b>CONTRATO / CUOTA:</b>', styles['Normal'])],
            ['Contrato:', contract.name or f'ID {contract.id}'],
            ['Cuota N°:', f'{installment.number} de {contract.installment_count}'],
            [
                'Vencimiento:',
                installment.due_date.strftime('%d/%m/%Y')
                if hasattr(installment.due_date, 'strftime')
                else str(installment.due_date),
            ],
        ]
        t_contract = Table(contract_data, colWidths=[2 * inch, 4 * inch])
        t_contract.setStyle(
            TableStyle(
                [
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3f4f6')),
                    ('SPAN', (0, 0), (1, 0)),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ]
            )
        )
        elements.append(t_contract)
        elements.append(Spacer(1, 15))

    date_str = payment.date.strftime('%d/%m/%Y %H:%M')

    concept_str = payment.notes if payment.notes else 'Servicios de Terapia'
    method_str = str(payment.method).upper()

    payment_data = [
        ['Fecha de Emisión:', date_str],
        ['Método de Pago:', method_str],
        ['Referencia:', payment.reference or '-'],
        ['Concepto:', concept_str],
    ]
    t_payment = Table(payment_data, colWidths=[2 * inch, 4 * inch])
    t_payment.setStyle(
        TableStyle(
            [
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t_payment)
    elements.append(Spacer(1, 20))

<<<<<<< HEAD
    amount_str = f'S/ {(payment.amount or 0):.2f}'
    discount_str = f'S/ {(payment.discount or 0):.2f}' if payment.discount else None
    net_str = f'S/ {((payment.amount or 0) - (payment.discount or 0)):.2f}'
=======
    amount_str = f'S/ {payment.amount:.2f}'
    discount_str = f'S/ {payment.discount:.2f}' if payment.discount else None
    net_str = f'S/ {payment.amount - (payment.discount or 0):.2f}'
>>>>>>> f1b7e09aa59329bf2cf74e154e23714089f13e80

    total_rows = [['', 'Subtotal:', amount_str]]
    if discount_str:
        total_rows.append(['', 'Descuento:', f'-{discount_str}'])
    total_rows.append(['', 'TOTAL PAGADO:', net_str])
    t_total = Table(total_rows, colWidths=[3.5 * inch, 1.5 * inch, 1 * inch])
    t_total.setStyle(
        TableStyle(
            [
                ('FONT', (1, -1), (2, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (1, -1), (2, -1), colors.HexColor('#65a30d')),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('LINEABOVE', (1, -1), (2, -1), 1, colors.black),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]
        )
    )
    elements.append(t_total)
    elements.append(Spacer(1, 40))

    elements.append(Paragraph('Este documento es un comprobante de control interno.', styles['Center']))
    elements.append(Paragraph('¡Gracias por confiar en el Centro de Terapias Juan Pablo II!', styles['Center']))

    doc.build(elements)
    buffer.seek(0)
    return buffer
