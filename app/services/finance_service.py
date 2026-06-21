from datetime import datetime

from sqlalchemy import func

from app.models import Appointment, Expense, User, db


class FinanceService:
    def get_expenses(self, start_date=None, end_date=None, category=None):
        q = Expense.query
        if start_date:
            q = q.filter(Expense.date >= start_date)
        if end_date:
            q = q.filter(Expense.date <= end_date)
        if category:
            q = q.filter(Expense.category == category)
        return q.order_by(Expense.date.desc()).all()

    def create_expense(self, data):
        try:
            date_val = data.get('date')
            if isinstance(date_val, str):
                date_val = datetime.strptime(date_val, '%Y-%m-%d')

            exp = Expense(
                category=data.get('category'),
                amount=float(data.get('amount')),
                date=date_val,
                description=data.get('description'),
                therapist_id=data.get('therapist_id'),
                method=data.get('method'),
                receipt_image_path=data.get('receipt_image_path'),
            )
            db.session.add(exp)
            db.session.commit()
            return True, exp
        except Exception as e:
            return False, str(e)

    def get_therapist_financials(self, month=None, year=None):
        if not month:
            month = datetime.now().month
        if not year:
            year = datetime.now().year

        therapists = User.query.filter_by(role='terapista', is_active=True).all()
        therapist_ids = [t.id for t in therapists]

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        minutes_by_therapist = {}
        paid_by_therapist = {}

        if therapist_ids:
            minutes_rows = db.session.query(
                Appointment.therapist_id,
                func.sum(Appointment.duration_minutes).label('total_minutes')
            ).filter(
                Appointment.therapist_id.in_(therapist_ids),
                Appointment.status == 'completed',
                Appointment.start_time >= start_date,
                Appointment.start_time < end_date
            ).group_by(Appointment.therapist_id).all()
            minutes_by_therapist = {row.therapist_id: row.total_minutes or 0 for row in minutes_rows}

            paid_rows = db.session.query(
                Expense.therapist_id,
                func.sum(Expense.amount).label('total_paid')
            ).filter(
                Expense.therapist_id.in_(therapist_ids),
                Expense.category == 'therapist_payment',
                Expense.date >= start_date,
                Expense.date < end_date
            ).group_by(Expense.therapist_id).all()
            paid_by_therapist = {row.therapist_id: row.total_paid or 0 for row in paid_rows}

        results = []
        for t in therapists:
            rate = 0
            if t.salary_base and t.contract_hours and t.contract_hours > 0:
                rate = t.salary_base / t.contract_hours

            worked_minutes = minutes_by_therapist.get(t.id, 0) or 0
            worked_hours = worked_minutes / 60
            projected_pay = rate * worked_hours
            paid_amount = paid_by_therapist.get(t.id, 0) or 0

            results.append(
                {
                    'therapist': t,
                    'rate': rate,
                    'contract_hours': t.contract_hours,
                    'worked_hours': worked_hours,
                    'projected_pay': projected_pay,
                    'paid': paid_amount,
                    'balance': projected_pay - paid_amount,
                }
            )

        return results
