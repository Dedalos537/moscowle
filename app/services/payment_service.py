from app.models import User, Payment, db
from app.services.email_service import EmailService
from app.services.notification_service import NotificationService
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

class PaymentService:
    def __init__(self):
        self.email_service = EmailService()
        self.notification_service = NotificationService()

    def get_patients_payment_status(self):
        """
        Returns a list of patients with their payment status explicitly calculated.
        """
        # In this system, patients have role='jugador'
        patients = User.query.filter_by(role='jugador').all()
        today = datetime.utcnow().date()
        
        results = []
        for p in patients:
            status = 'active'
            days_overdue = 0
            
            if not p.is_active:
                status = 'inactive'
            elif p.payment_due_date and p.payment_due_date < today:
                status = 'overdue'
                days_overdue = (today - p.payment_due_date).days
                # Auto-deactivate check (could be done here or separately)
                # For this MVP, we flag it. Actual deactivation happens in a separate method.
            
            latest_payment = Payment.query.filter_by(patient_id=p.id).order_by(Payment.date.desc()).first()
            
            results.append({
                'user': p,
                'status': status, # active, inactive, overdue
                'full_status_label': 'Al día' if status == 'active' else 'Vencido' if status == 'overdue' else 'Inactivo',
                'days_overdue': days_overdue,
                'last_payment_date': latest_payment.date if latest_payment else None,
                'last_payment_amount': latest_payment.amount if latest_payment else None
            })
        return results

    def register_payment(self, patient_id, amount, method, reference, next_due_date_str, receipt_path=None, discount=0.0):
        """
        Registers a payment and updates user status.
        """
        user = User.query.get(patient_id)
        if not user:
            return False, "Usuario no encontrado"

        try:
            # 1. Create Payment Record
            new_payment = Payment(
                patient_id=patient_id,
                amount=amount,
                method=method,
                reference=reference,
                receipt_image_path=receipt_path,
                discount=discount,
                date=datetime.utcnow()
            )
            db.session.add(new_payment)
            
            # 2. Update User
            user.payment_amount = amount # Update current plan amount if needed, or just track history? 
            # Assuming payment_amount on user is the 'agreed monthly amount', let's not overwrite it with this transaction unless intent is to update plan.
            # But the requirement says "assign a payment date".
            
            if next_due_date_str:
                user.payment_due_date = datetime.strptime(next_due_date_str, '%Y-%m-%d').date()
            
            # Reactivate if they were inactive due to non-payment
            if not user.is_active:
                # Logic: If paying, we assume they are reactivating. 
                # Ideally check if payment covers debt, but for MVP: pay = activate.
                user.is_active = True
                
            db.session.commit()
            return True, "Pago registrado exitosamente"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def update_payment_settings(self, patient_id, amount, due_date_str, frequency):
        """
        Updates the payment plan for a user.
        """
        user = User.query.get(patient_id)
        if not user:
            return False, "Usuario no encontrado"
            
        try:
            if amount:
                user.payment_amount = float(amount)
            if due_date_str:
                user.payment_due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
            if frequency:
                user.payment_plan = frequency
                
            db.session.commit()
            return True, "Configuración actualizada"
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def check_and_deactivate_overdue(self):
        """
        Checks all users and deactivates those who passed their due date.
        """
        today = datetime.utcnow().date()
        overdue_users = User.query.filter(
            User.role == 'jugador',
            User.is_active == True,
            User.payment_due_date < today
        ).all()
        
        count = 0
        for user in overdue_users:
            user.is_active = False # Deactivate!
            count += 1
        
        if count > 0:
            db.session.commit()
        
        return count

    def check_upcoming_due_dates(self):
        """
        Periodically checks for upcoming payments to send reminders.
        """
        # Look for users with due_date in exactly 3 days or 0 days (today)
        target_users = User.query.filter(User.role == 'jugador', User.is_active == True, User.payment_due_date.isnot(None)).all()
        today = datetime.utcnow().date()
        
        sent_count = 0
        for user in target_users:
            if not user.payment_due_date:
                continue
                
            delta = (user.payment_due_date - today).days
            
            # Send reminder if 3 days left or 0 days left (today)
            if delta == 3 or delta == 0:
                is_urgent = delta == 0
                
                # 1. Email
                self.email_service.send_payment_reminder(
                    user.email, 
                    user.username, 
                    delta, 
                    user.payment_due_date, 
                    user.payment_amount or 0
                )
                
                # 2. Internal Notification
                msg = f"⚠️ Tu pago de S/ {user.payment_amount} vence {'HOY' if is_urgent else 'en 3 días'}. Por favor regulariza para evitar bloqueos."
                self.notification_service.create_notification(user.id, msg, link='/patient/dashboard')
                
                sent_count += 1
                
        return sent_count

    def get_billing_info(self, patient_id):
        """
        Calculates suggested next billing date and checks for unbilled absences.
        """
        user = User.query.get(patient_id)
        if not user:
            return None

        # 1. Calculate Suggested Next Due Date
        today = datetime.utcnow().date()
        base_date = user.payment_due_date if user.payment_due_date else today
        
        # If the due date is in the past, maybe we should start from today? 
        # Usually we want to extend from the previous expiration to keep the cycle.
        # But if it's way in the past, maybe reset to today + cycle.
        # For now, let's just add to base_date to be consistent with subscription logic.
        
        suggested_date = None
        if user.payment_plan == 'quincenal':
            suggested_date = base_date + timedelta(days=15)
        else: # default monthly
            # Add month logic handling end of month
            month = base_date.month % 12 + 1
            year = base_date.year + (base_date.month // 12)
            try:
                suggested_date = base_date.replace(year=year, month=month)
            except ValueError:
                # Handle cases like Jan 31 -> Feb 28
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                suggested_date = base_date.replace(year=year, month=month, day=last_day)

        # 2. Count Absences since last payment
        # Find last payment date
        last_payment = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).first()
        last_payment_date = last_payment.date if last_payment else datetime.min
        
        # Query absences
        # We need to filter appointments where status='completed' (or scheduled/past?) AND attendance='absent'
        # And date > last_payment_date
        absences_count = Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.attendance == 'absent',
            Appointment.start_time > last_payment_date
        ).count()

        return {
            'suggested_date': suggested_date.strftime('%Y-%m-%d'),
            'absences': absences_count,
            'current_plan': user.payment_plan,
            'current_amount': user.payment_amount
        }
    
    def get_financial_summary(self):
        """
        Returns financial metrics for the dashboard/reports.
        """
        today = datetime.utcnow().date()
        
        # 1. Monthly Income (Real) - Current Month
        start_date = today.replace(day=1)
        import calendar
        last_day = calendar.monthrange(today.year, today.month)[1]
        end_date = today.replace(day=last_day)
        
        income_query = db.session.query(func.sum(Payment.amount)).filter(
            Payment.date >= start_date,
            Payment.date <= end_date.strftime('%Y-%m-%d 23:59:59')
        ).scalar()
        
        monthly_income_real = income_query or 0.0
        
        # 2. Monthly Expected Income (Estimated)
        # Sum of all active players' payment_amount
        # This is a rough estimate assuming everyone pays once a month or according to their plan in this month
        # For 'quincenal', multiple by 2? Let's keep it simple sum for now or refine.
        active_players = User.query.filter_by(role='jugador', is_active=True).all()
        monthly_income_expected = 0.0
        for p in active_players:
            amt = p.payment_amount or 0
            if p.payment_plan == 'quincenal':
                monthly_income_expected += (amt * 2)
            else:
                monthly_income_expected += amt
                
        # 3. Delinquency (Morosidad)
        # Sum of payment_amount for overdue users
        overdue_users = User.query.filter(
            User.role == 'jugador',
            User.payment_due_date < today
        ).all()
        
        overdue_amount = sum([u.payment_amount or 0 for u in overdue_users])
        
        return {
            'month_name': start_date.strftime('%B'),
            'income_real': monthly_income_real,
            'income_expected': monthly_income_expected,
            'overdue_amount': overdue_amount,
            'overdue_users_count': len(overdue_users)
        }
