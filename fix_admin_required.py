import re

filepath = 'app/routes/admin_routes.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

old_route = """@admin_bp.route('/payments/<int:payment_id>/receipt')
@login_required
@admin_required
def download_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)"""

new_route = """@admin_bp.route('/payments/<int:payment_id>/receipt')
@login_required
def download_receipt(payment_id):
    from flask import flash, redirect, url_for
    from flask_login import current_user
    
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)"""

content = content.replace(old_route, new_route)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed admin_required decorator issue.")
