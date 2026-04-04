#!/usr/bin/env python3
"""Test script to verify deudores and payment system"""

from app import create_app
from app.models import User, Payment
from datetime import datetime

app = create_app()

with app.app_context():
    # Find deudores (overdue patients)
    users = User.query.filter_by(role='jugador').all()
    overdue_users = []
    
    today = datetime.utcnow().date()
    for u in users:
        if u.payment_due_date and u.payment_due_date < today:
            days_late = (today - u.payment_due_date).days
            overdue_users.append({
                'id': u.id,
                'name': u.username,
                'due_date': u.payment_due_date,
                'days_late': days_late,
                'active': u.is_active,
                'amount': u.payment_amount
            })
    
    print("\n" + "=" * 70)
    print("OVERDUE PATIENTS (DEUDORES) - BEFORE PAYMENT TEST")
    print("=" * 70)
    if overdue_users:
        for user in sorted(overdue_users, key=lambda x: x['days_late'], reverse=True)[:5]:
            status = "ACTIVE" if user['active'] else "INACTIVE"
            print(f"  ID: {user['id']:3d} | Name: {user['name']:15s} | Days Late: {user['days_late']:3d} | Amount: S/{user['amount']:7.2f} | Status: {status}")
    else:
        print("  No overdue patients found")
    print()
    
    # Get recent payments
    recent_payments = Payment.query.order_by(Payment.date.desc()).limit(3).all()
    print("=" * 70)
    print("RECENT PAYMENTS")
    print("=" * 70)
    for p in recent_payments:
        patient = User.query.get(p.patient_id)
        print(f"  Patient: {patient.username:15s} | Amount: S/{p.amount:7.2f} | Method: {p.method:12s} | Date: {p.date}")
    
    print("\n✅ Test script completed successfully")
