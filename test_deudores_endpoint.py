import sys
sys.path.insert(0, '/Users/apple/Documents/moscowle_ia_mvp')

from app import create_app
from datetime import datetime, timedelta

app = create_app()

with app.app_context():
    # Query deudores using the CORRECTED logic
    today = datetime.utcnow().date()
    week_ahead = today + timedelta(days=7)
    
    from app.models import User, Sede
    
    patients = User.query.filter_by(role='jugador', is_active=True).all()
    
    print(f"\n=== DEUDORES TEST (OVERDUE + UPCOMING) ===")
    print(f"Today: {today}")
    print(f"Week ahead: {week_ahead}")
    print(f"Total active patients: {len(patients)}\n")
    
    deudor_count = 0
    vencidos = []
    proximos = []
    
    for patient in patients:
        due_date = patient.payment_due_date
        
        # Include both overdue and upcoming
        if not due_date or due_date >= week_ahead:
            continue
        
        days_diff = (today - due_date).days
        monto = patient.payment_amount or 0
        
        if due_date < today:
            vencidos.append((patient.username or patient.email, due_date, days_diff, monto))
        elif today <= due_date <= week_ahead:
            proximos.append((patient.username or patient.email, due_date, days_diff, monto))
        
        deudor_count += 1
    
    print(f"🔴 VENCIDOS:")
    for name, due_date, days, monto in vencidos:
        print(f"  ✓ {name} - Due: {due_date} (Overdue: {days} days) - S/ {monto}")
    
    print(f"\n🟠 PRÓXIMOS A VENCER:")
    for name, due_date, days, monto in proximos:
        days_remaining = (due_date - today).days
        print(f"  ✓ {name} - Due: {due_date} (En {days_remaining} días) - S/ {monto}")
    
    print(f"\n✓ Total deudores (overdue + upcoming): {deudor_count}")
    print(f"  - Vencidos: {len(vencidos)}")
    print(f"  - Próximos a vencer: {len(proximos)}")
