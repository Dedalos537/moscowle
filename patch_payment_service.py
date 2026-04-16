import re

with open('app/services/payment_service.py', 'r') as f:
    content = f.read()

old_code = """
        return {
            'suggested_date': suggested_date.strftime('%Y-%m-%d'),
            'suggested_sessions': max(1, suggested_sessions + to_recover),
            'recovery_msg': f"Ajuste de {to_recover} sesiones (pendientes: {remaining})" if to_recover != 0 else None,
            'current_plan': user.payment_plan,
            'current_amount': user.payment_amount or 0.0,
            'absences': user.sessions_total - user.sessions_attended if user.sessions_total > user.sessions_attended else 0
        }
"""

new_code = """
        return {
            'suggested_date': suggested_date.strftime('%Y-%m-%d'),
            'suggested_sessions': max(1, suggested_sessions + to_recover),
            'recovery_msg': f"Ajuste de {to_recover} sesiones (pendientes: {remaining})" if to_recover != 0 else None,
            'current_plan': user.payment_plan,
            'current_amount': user.payment_amount or 0.0,
            'absences': user.sessions_total - user.sessions_attended if user.sessions_total > user.sessions_attended else 0,
            'document_number': user.document_number,
            'guardian_name': user.guardian_name
        }
"""

content = content.replace(old_code, new_code)

with open('app/services/payment_service.py', 'w') as f:
    f.write(content)
