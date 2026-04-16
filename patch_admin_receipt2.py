with open('app/routes/admin_routes.py', 'r') as f:
    text = f.read()

import re

old_string = """    if not patient:
        flash("Paciente no encontrado para este pago.", "error")
        return redirect(url_for('admin.users'))

    pdf_buffer = generate_receipt_pdf(payment, patient)"""

new_string = """    if not patient:
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

    pdf_buffer = generate_receipt_pdf(payment, patient)"""

text = text.replace(old_string, new_string)
text = text.replace("@admin_bp.route('/payments/<int:payment_id>/receipt')", "@admin_bp.route('/payments/<int:payment_id>/receipt', methods=['GET', 'POST'])")

with open('app/routes/admin_routes.py', 'w') as f:
    f.write(text)
print("Route fixed")
