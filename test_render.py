from app import create_app
from app.models import User, Payment
from flask import render_template
app = create_app()
with app.test_request_context('/admin/payments/history/16'):
    try:
        from app.routes.admin_routes import admin_bp
        from app.services.payment_service import PaymentService
        patient = User.query.get(16)
        ps = PaymentService()
        payment_history = ps.get_payment_history(16)
        html = render_template('admin/payment_history.html', patient=patient, payment_history=payment_history, active_page='admin_payments')
        print("Success")
    except Exception as e:
        import traceback
        traceback.print_exc()
