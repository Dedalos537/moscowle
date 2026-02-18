from app import create_app, db
from app.models import User, Appointment, SessionMetrics
from sqlalchemy import func
from app.services.payment_service import PaymentService

app = create_app()

with app.app_context():
    print("Testing logic in admin/reports...")
    
    # Mocking what happens in the route
    try:
        therapists = User.query.filter_by(role='terapista').all()
        print(f"Found {len(therapists)} therapists.")
        
        for t in therapists:
            print(f"Processing therapist {t.username} (ID: {t.id})")
            count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
            
            # This is the new query I added
            print("Executing avg_acc query...")
            avg_acc = db.session.query(func.avg(SessionMetrics.accurracy))\
                .join(Appointment, SessionMetrics.session_id == Appointment.id)\
                .filter(Appointment.therapist_id == t.id).scalar() or 0
            
            print(f"  Sessions: {count_appts}, Avg Acc: {avg_acc}")

        print("Testing PaymentService...")
        payment_service = PaymentService()
        financials = payment_service.get_financial_summary()
        print("Financials:", financials)
        
        print("SUCCESS: Logic executed without errors.")

    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()
