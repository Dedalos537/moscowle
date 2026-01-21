import sys
import os
from datetime import datetime

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Payment

def create_payment(email, amount, date_str):
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if not user:
            print(f"Error: User with email {email} not found.")
            return
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print("Error: Date must be YYYY-MM-DD")
            return

        payment = Payment(
            patient_id=user.id,
            amount=float(amount),
            date=date_obj,
            method='manual_script',
            reference='Manual Entry via Script',
            status='completed' 
        )
        db.session.add(payment)
        
        # Note: This script only inserts the payment record. 
        # It does not update the user's due date automatically.
        # Use the Admin UI for full logic if needed.
             
        db.session.commit()
        print(f"Successfully added payment of {amount} for {user.username} on {date_str}.")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python manual_payment_entry.py <email> <amount> <YYYY-MM-DD>")
        sys.exit(1)
    
    create_payment(sys.argv[1], sys.argv[2], sys.argv[3])
