from app import create_app
from app.models import Payment, User
from app.services.receipt_generator import generate_receipt_pdf

app = create_app()
with app.app_context():
    payment = Payment.query.get(42)
    if not payment:
        print("Payment 42 not found")
    else:
        patient = User.query.get(payment.patient_id)
        try:
            generate_receipt_pdf(payment, patient)
            print("Success for 42")
        except Exception as e:
            import traceback
            traceback.print_exc()

