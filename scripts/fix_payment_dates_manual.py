from app import create_app
from app.extensions import db
from app.models import User, Payment
from datetime import datetime

# Initialize app context
# Using create_app directly, skipping extra scheduler setup in run.py
app = create_app()

def run_fix():
    with app.app_context():
        # --- FIX FOR DIEGO ---
        # Search for Diego
        print("Searching for Diego...")
        diego_list = User.query.filter(User.username.ilike('%diego%')).all()
        diego = None
        for u in diego_list:
            # Check for 'arrunategui' or assume the first 'diego' is correct if unique
            if 'arrunategui' in u.username.lower() or 'zapata' in u.username.lower():
                diego = u
                break
        
        # If not found by specific name, take first Diego
        if not diego and diego_list:
            diego = diego_list[0]

        if diego:
            print(f"User Diego found: {diego.username} (ID: {diego.id})")
            # Find recent payments (focus on December or Feb misdated)
            payments = Payment.query.filter_by(patient_id=diego.id).order_by(Payment.date.desc()).limit(10).all()
            
            target_p = None
            # He wants to change "pagos registrados en diciembre" to Feb 17
            for p in payments:
                # Check if month is 12 (December)
                if p.date.month == 12:
                    target_p = p
                    break
            
            if target_p:
                print(f"Found Payment ID {target_p.id} with date {target_p.date}. Updating to Feb 17, 2026.")
                # Update date
                new_date = target_p.date.replace(year=2026, month=2, day=17)
                target_p.date = new_date
            else:
                print("No December payment found for Diego. Listing recent:")
                for p in payments:
                    print(f" - ID {p.id}: {p.date}")
        else:
            print("User Diego not found.")

        # --- FIX FOR SAMANTA ---
        print("\nSearching for Samanta...")
        samanta = User.query.filter(User.username.ilike('%samanta%')).first()
        
        if samanta:
            print(f"User Samanta found: {samanta.username} (ID: {samanta.id})")
            payments = Payment.query.filter_by(patient_id=samanta.id).order_by(Payment.date.desc()).limit(10).all()
            
            target_p = None
            # She wants to change "pagos registrados en diciembre" to Feb 7
            for p in payments:
                if p.date.month == 12:
                    target_p = p
                    break
            
            if target_p:
                print(f"Found Payment ID {target_p.id} with date {target_p.date}. Updating to Feb 7, 2026.")
                new_date = target_p.date.replace(year=2026, month=2, day=7)
                target_p.date = new_date
            else:
                print("No December payment found for Samanta. Listing recent:")
                for p in payments:
                    print(f" - ID {p.id}: {p.date}")
        else:
            print("User Samanta not found.")

        # Commit changes
        try:
            db.session.commit()
            print("\nDatabase updated successfully.")
        except Exception as e:
            db.session.rollback()
            print(f"\nError committing changes: {e}")

if __name__ == '__main__':
    run_fix()
