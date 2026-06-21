from calendar import monthrange
from datetime import datetime

from sqlalchemy import func

from app.models import Contract, Installment, Payment, User, db


class ContractService:
    def create_contract(self, patient_id, total_amount, installment_count=4, name=None, start_date=None, notes=None):
        """Create contract and auto-generate installments"""
        patient = User.query.get(patient_id)
        if not patient:
            return False, 'Paciente no encontrado'

        if not start_date:
            start_date = datetime.utcnow().date()

        installment_amount = round(total_amount / installment_count, 2)

        contract = Contract(
            patient_id=patient_id,
            name=name or f'Plan Terapias {start_date.strftime("%b %Y")}',
            total_amount=total_amount,
            installment_count=installment_count,
            installment_amount=installment_amount,
            start_date=start_date,
            status='active',
            notes=notes,
        )
        db.session.add(contract)
        db.session.flush()

        due_date = start_date
        for i in range(1, installment_count + 1):
            if i > 1:
                next_month = due_date.month % 12 + 1
                next_year = due_date.year + (due_date.month // 12)
                last_day = monthrange(next_year, next_month)[1]
                target_day = min(due_date.day, last_day)
                due_date = due_date.replace(year=next_year, month=next_month, day=target_day)

            installment = Installment(
                contract_id=contract.id,
                number=i,
                due_date=due_date,
                amount=installment_amount,
                status='pending',
            )
            db.session.add(installment)

        db.session.commit()
        return True, contract

    def get_patient_contracts(self, patient_id):
        """Get all contracts for a patient with installment counts"""
        contracts = Contract.query.filter_by(patient_id=patient_id).order_by(Contract.created_at.desc()).all()
        result = []
        for c in contracts:
            total = len(c.installments)
            paid = sum(1 for i in c.installments if i.status == 'paid')
            overdue = sum(1 for i in c.installments if i.status == 'overdue')
            result.append(
                {
                    'id': c.id,
                    'name': c.name,
                    'total_amount': c.total_amount,
                    'installment_count': total,
                    'installment_amount': c.installment_amount,
                    'paid_count': paid,
                    'overdue_count': overdue,
                    'status': c.status,
                    'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else None,
                    'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else None,
                    'notes': c.notes,
                }
            )
        return result

    def get_contract_detail(self, contract_id):
        """Get contract with all installments"""
        contract = Contract.query.get(contract_id)
        if not contract:
            return None

        installments = []
        for inst in contract.installments:
            installments.append(
                {
                    'id': inst.id,
                    'number': inst.number,
                    'due_date': inst.due_date.strftime('%Y-%m-%d'),
                    'amount': inst.amount,
                    'paid_amount': inst.paid_amount,
                    'paid_date': inst.paid_date.strftime('%Y-%m-%d %H:%M') if inst.paid_date else None,
                    'status': inst.status,
                    'reminder_sent': inst.reminder_sent,
                    'payment_id': inst.payment_id,
                }
            )

        return {
            'id': contract.id,
            'patient_id': contract.patient_id,
            'name': contract.name,
            'total_amount': contract.total_amount,
            'installment_count': contract.installment_count,
            'installment_amount': contract.installment_amount,
            'start_date': contract.start_date.strftime('%Y-%m-%d') if contract.start_date else None,
            'status': contract.status,
            'notes': contract.notes,
            'installments': installments,
        }

    def pay_installment(
        self, installment_id, amount, method, reference=None, payment_date=None, discount=0.0, receipt_path=None
    ):
        """Register payment against an installment"""
        installment = Installment.query.get(installment_id)
        if not installment:
            return False, 'Cuota no encontrada'

        if installment.status == 'paid':
            return False, 'Esta cuota ya está pagada'

        try:
            payment_datetime = payment_date or datetime.utcnow()

            new_payment = Payment(
                patient_id=installment.contract.patient_id,
                amount=amount,
                method=method,
                reference=reference,
                receipt_image_path=receipt_path,
                discount=discount,
                date=payment_datetime,
                installment_id=installment.id,
            )
            db.session.add(new_payment)
            db.session.flush()

            installment.paid_amount = (installment.paid_amount or 0) + amount
            installment.paid_date = payment_datetime
            installment.payment_id = new_payment.id

            total_paid = (
                db.session.query(func.sum(Payment.amount)).filter(Payment.installment_id == installment.id).scalar()
                or 0
            )

            if total_paid >= installment.amount:
                installment.status = 'paid'
            else:
                installment.status = 'partial'

            db.session.commit()

            return True, new_payment

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def get_due_installments(self, reference_date=None):
        """Get all overdue installments for debt collection"""
        if not reference_date:
            reference_date = datetime.utcnow().date()

        overdue = (
            Installment.query.filter(
                Installment.status.in_(['pending', 'partial']), Installment.due_date < reference_date
            )
            .order_by(Installment.due_date.asc())
            .all()
        )

        result = []
        for inst in overdue:
            contract = Contract.query.get(inst.contract_id)
            patient = User.query.get(contract.patient_id) if contract else None
            days_overdue = (reference_date - inst.due_date).days if inst.due_date else 0
            result.append(
                {
                    'installment_id': inst.id,
                    'contract_id': inst.contract_id,
                    'contract_name': contract.name if contract else '',
                    'patient_id': patient.id if patient else None,
                    'patient_name': patient.username if patient else '',
                    'patient_phone': patient.phone if patient else '',
                    'due_date': inst.due_date.strftime('%Y-%m-%d') if inst.due_date else None,
                    'amount': inst.amount,
                    'paid_amount': inst.paid_amount,
                    'remaining': inst.amount - (inst.paid_amount or 0),
                    'days_overdue': days_overdue,
                    'number': inst.number,
                    'reminder_sent': inst.reminder_sent,
                }
            )
        return result

    def get_debt_summary(self):
        """Aggregate debt across all contracts — replaces get_patients_payment_status debt calc"""
        today = datetime.utcnow().date()

        patients_with_debt = (
            db.session.query(
                Installment.contract_id,
                Contract.patient_id,
                func.sum(Installment.amount - func.coalesce(Installment.paid_amount, 0)).label('total_debt'),
            )
            .join(Contract, Installment.contract_id == Contract.id)
            .filter(
                Contract.status == 'active',
                Installment.status.in_(['pending', 'partial']),
                Installment.due_date < today,
            )
            .group_by(Installment.contract_id, Contract.patient_id)
            .all()
        )

        return [
            {
                'patient_id': row.patient_id,
                'contract_id': row.contract_id,
                'total_debt': float(row.total_debt),
            }
            for row in patients_with_debt
        ]
