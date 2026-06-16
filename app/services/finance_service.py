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

        therapists = User.query.filter_by(role='terapista').filter_by(is_active=True).all()
        results = []

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        for t in therapists:
            rate = 0
            if t.salary_base and t.contract_hours and t.contract_hours > 0:
                rate = t.salary_base / t.contract_hours

            worked_minutes = (
                db.session.query(func.sum(Appointment.duration_minutes))
                .filter(Appointment.therapist_id == t.id)
                .filter(Appointment.status == 'completed')
                .filter(Appointment.start_time >= start_date)
                .filter(Appointment.start_time < end_date)
                .scalar()
                or 0
            )

            worked_hours = worked_minutes / 60

            projected_pay = rate * worked_hours

            paid_amount = (
                db.session.query(func.sum(Expense.amount))
                .filter(Expense.therapist_id == t.id)
                .filter(Expense.category == 'therapist_payment')
                .filter(Expense.date >= start_date)
                .filter(Expense.date < end_date)
                .scalar()
                or 0
            )

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
