#!/usr/bin/env python3
"""Test payment registration and mora reset"""

from app import create_app
from app.models import User, Payment
from app.services.payment_service import PaymentService
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    payment_service = PaymentService()
    
    # Test patient: Domenica (ID 28, 7 days overdue)
    test_patient_id = 28
    patient = User.query.get(test_patient_id)
    
    print("\n" + "=" * 70)
    print("PAYMENT MORA RESET TEST")
    print("=" * 70)
    
    print(f"\n📋 TEST PATIENT: {patient.username} (ID: {test_patient_id})")
    print(f"   Current State:")
    print(f"   - payment_due_date: {patient.payment_due_date}")
    print(f"   - is_active: {patient.is_active}")
    print(f"   - payment_amount: S/{patient.payment_amount}")
    
    # Calculate expected next due date
    today = datetime.utcnow().date()
    next_due = today + timedelta(days=30)  # Assuming monthly cycle
    
    print(f"\n💳 Processing Payment:")
    print(f"   - Amount: S/{patient.payment_amount}")
    print(f"   - Method: test_method")
    print(f"   - Next Due Date: {next_due}")
    
    # Call register_payment
    success, message = payment_service.register_payment(
        patient_id=test_patient_id,
        amount=patient.payment_amount,
        method='test_method',
        reference='TEST-001',
        next_due_date_str=next_due.strftime('%Y-%m-%d'),
        receipt_path=None,
        discount=0.0,
        payment_date=datetime.utcnow()
    )
    
    print(f"\n✅ Payment Registration Result: {message}")
    
    # Refresh user data
    patient = User.query.get(test_patient_id)
    
    print(f"\n📋 TEST PATIENT AFTER PAYMENT:")
    print(f"   - payment_due_date: {patient.payment_due_date}")
    print(f"   - is_active: {patient.is_active}")
    
    # Verify changes
    today = datetime.utcnow().date()
    is_still_overdue = patient.payment_due_date and patient.payment_due_date < today
    
    print(f"\n🔍 VERIFICATION:")
    print(f"   - payment_due_date updated? {'✅ YES' if patient.payment_due_date >= next_due - timedelta(days=1) else '❌ NO'}")
    print(f"   - is_active restored? {'✅ YES' if patient.is_active else '❌ NO'}")
    print(f"   - still overdue? {'❌ YES' if is_still_overdue else '✅ NO'}")
    
    if not is_still_overdue and patient.is_active and patient.payment_due_date >= next_due - timedelta(days=1):
        print("\n✅ MORA RESET SUCCESSFUL - Patient should disappear from deudores list")
    else:
        print("\n❌ MORA RESET FAILED - Check backend logic")
    
    print()
