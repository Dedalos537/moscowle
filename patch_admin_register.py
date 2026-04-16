import re

with open('app/routes/admin_routes.py', 'r') as f:
    content = f.read()

# Buscamos donde saca los campos
old_code = """
    # Convert payment_date if provided
    payment_date_obj = None
    if payment_date_str:
"""

new_code = """
    # Convert payment_date if provided
    payment_date_obj = None
    if payment_date_str:
"""

# And where to save it
old_code2 = """    success, result_or_payment = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)"""

new_code2 = """
    document_number = request.form.get('document_number')
    guardian_name = request.form.get('guardian_name')
    
    if document_number or guardian_name:
        patient = User.query.get(patient_id)
        if patient:
            if document_number: patient.document_number = document_number
            if guardian_name: patient.guardian_name = guardian_name
            db.session.commit()

    success, result_or_payment = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)"""

content = content.replace(old_code2, new_code2)

with open('app/routes/admin_routes.py', 'w') as f:
    f.write(content)
print("Admin routes patched")
