import re

filepath = 'app/routes/admin_routes.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Add the new imports if they don't exist
if 'from flask import send_file' not in content:
    content = content.replace('from flask import render_template', 'from flask import render_template, send_file')

if 'from app.services.receipt_generator import generate_receipt_pdf' not in content:
    content = 'from app.services.receipt_generator import generate_receipt_pdf\n' + content

# Add the new route right before the end or after view_patient
new_route = """
@admin_bp.route('/payments/<int:payment_id>/receipt')
@login_required
@admin_required
def download_receipt(payment_id):
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

if 'def download_receipt' not in content:
    content += new_route

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated admin routes.")
