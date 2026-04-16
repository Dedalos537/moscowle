import re

with open('app/routes/admin_routes.py', 'r') as f:
    content = f.read()

old_route = """@admin_bp.route('/payments/<int:payment_id>/receipt')
@login_required
def download_receipt(payment_id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)
    
    if not patient:
        flash("Paciente no encontrado para este pago.", "error")
        return redirect(url_for('admin.users'))

    pdf_buffer = generate_receipt_pdf(payment, patient)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Recibo_JP2_REC-{payment.id:06d}.pdf",
        mimetype='application/pdf'
    )
"""

new_route = """@admin_bp.route('/payments/<int:payment_id>/receipt', methods=['GET', 'POST'])
@login_required
def download_receipt(payment_id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)
    
    if not patient:
        flash("Paciente no encontrado para este pago.", "error")
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        # Retrieve fields to rectify
        doc_number = request.form.get('document_number')
        g_name = request.form.get('guardian_name')
        concept = request.form.get('concept')
        
        # Save rectified data for the future
        if doc_number: patient.document_number = doc_number
        if g_name: patient.guardian_name = g_name
        if concept: payment.notes = concept
        
        db.session.commit()

    pdf_buffer = generate_receipt_pdf(payment, patient)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Recibo_JP2_REC-{payment.id:06d}.pdf",
        mimetype='application/pdf'
    )
"""

content = content.replace(old_route, new_route)

with open('app/routes/admin_routes.py', 'w') as f:
    f.write(content)
