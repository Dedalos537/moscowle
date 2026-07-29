from calendar import monthrange
from datetime import date, datetime

from sqlalchemy import func

from app.models import Contract, Installment, Payment, User, db


class ContractService:
    def create_contract(
        self,
        patient_id,
        total_amount,
        installment_count=4,
        name=None,
        start_date=None,
        notes=None,
        billing_type='Mensual',
        currency='PEN',
        bonus_months=0,
        billing_rule='standard',
        implementation_cost=0.0,
    ):
        patient = User.query.get(patient_id)
        if not patient:
            return False, 'Paciente no encontrado'

        if not start_date:
            start_date = datetime.utcnow().date()
        elif isinstance(start_date, str):
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()

        sign_date = start_date
        service_start_date = start_date

        installment_amount = round(total_amount / installment_count, 2) if installment_count else 0

        contract = Contract(
            patient_id=patient_id,
            name=name or f'Plan Terapias {start_date.strftime("%b %Y")}',
            total_amount=total_amount,
            installment_count=installment_count,
            installment_amount=installment_amount,
            start_date=start_date,
            end_date=None,
            status='active',
            notes=notes,
            billing_type=billing_type,
            currency=currency,
            bonus_months=bonus_months,
            sign_date=sign_date,
            service_start_date=service_start_date,
            billing_rule=billing_rule,
            implementation_cost=implementation_cost,
        )
        db.session.add(contract)
        db.session.flush()

        installments = self._generate_installments(
            billing_type=billing_type,
            price=installment_amount,
            duration=installment_count,
            bonus=bonus_months,
            sign_date=sign_date,
            start_date=service_start_date,
            billing_rule=billing_rule,
            implementation_cost=implementation_cost,
            currency=currency,
        )

        for inst_data in installments:
            installment = Installment(
                contract_id=contract.id,
                number=inst_data['number'],
                due_date=inst_data['due_date'],
                amount=inst_data['amount'],
                status='pending',
                description=inst_data.get('description'),
                is_implementation=inst_data.get('is_implementation', False),
            )
            db.session.add(installment)

        db.session.commit()
        return True, contract

    def _generate_installments(
        self,
        billing_type,
        price,
        duration,
        bonus,
        sign_date,
        start_date,
        billing_rule,
        implementation_cost,
        currency,
    ):
        installments = []

        if implementation_cost > 0:
            installments.append(
                {
                    'number': 0,
                    'due_date': sign_date,
                    'amount': float(implementation_cost),
                    'status': 'pending',
                    'description': 'Costo de Implementación',
                    'is_implementation': True,
                }
            )

        if billing_type == 'Anual':
            months_to_pay = duration - bonus
            total_value = price * months_to_pay
            installments.append(
                {
                    'number': 1,
                    'due_date': sign_date,
                    'amount': round(total_value, 2),
                    'status': 'pending',
                    'description': 'Pago Anual Anticipado',
                    'is_implementation': False,
                }
            )
        else:
            if billing_rule == 'sign-date':
                due_dates = self._get_sign_date_due_dates(sign_date, duration)
            else:
                due_dates = self._get_standard_due_dates(start_date, duration)

            for i in range(duration):
                installments.append(
                    {
                        'number': i + 1,
                        'due_date': due_dates[i],
                        'amount': price,
                        'status': 'pending',
                        'description': f'Cuota Mensual {i + 1}',
                        'is_implementation': False,
                    }
                )

        return installments

    def _get_standard_due_dates(self, start_date, count):
        dates = []
        target_day = start_date.day
        for i in range(count):
            year = start_date.year + (start_date.month + i - 1) // 12
            month = (start_date.month + i - 1) % 12 + 1
            last_day = monthrange(year, month)[1]
            day = min(target_day, last_day)
            dates.append(date(year, month, day))
        return dates

    def _get_sign_date_due_dates(self, sign_date, count):
        dates = []
        pay_day = sign_date.day
        is_first_half = pay_day <= 15

        if is_first_half:
            first_due_month = sign_date.month
            first_due_year = sign_date.year
            last_day = monthrange(first_due_year, first_due_month)[1]
            dates.append(date(first_due_year, first_due_month, last_day))
        else:
            next_month = sign_date.month % 12 + 1
            next_year = sign_date.year + (sign_date.month // 12)
            dates.append(date(next_year, next_month, 15))

        base = dates[0]
        for i in range(1, count):
            if is_first_half:
                year = base.year + (base.month + i - 1) // 12
                month = (base.month + i - 1) % 12 + 1
                last_day = monthrange(year, month)[1]
                dates.append(date(year, month, last_day))
            else:
                year = base.year + (base.month + i - 1) // 12
                month = (base.month + i - 1) % 12 + 1
                dates.append(date(year, month, 15))

        return dates

    def get_patient_contracts(self, patient_id):
        contracts = Contract.query.filter_by(patient_id=patient_id).order_by(Contract.created_at.desc()).all()
        return [self._contract_summary(c) for c in contracts]

    def get_all_contracts(self, status=None, limit=200):
        q = Contract.query
        if status:
            q = q.filter_by(status=status)
        contracts = q.order_by(Contract.created_at.desc()).limit(limit).all()
        return [self._contract_summary(c) for c in contracts]

    def get_contracts_filtered(self, search=None, status=None, month=None, year=None, sede_id=None, limit=200):
        q = Contract.query

        if status and status != 'todos':
            if status == 'deudor':
                today = datetime.utcnow().date()
                q = q.join(Installment).filter(
                    Installment.status.in_(['pending', 'partial']),
                    Installment.due_date < today,
                )
            else:
                q = q.filter_by(status=status)

        if sede_id:
            q = q.join(User, Contract.patient_id == User.id).filter(User.sede_id == sede_id)

        if search:
            term = f'%{search}%'
            q = q.join(User, Contract.patient_id == User.id).filter(
                db.or_(User.username.ilike(term), User.email.ilike(term))
            )

        contracts = q.order_by(Contract.created_at.desc()).limit(limit).all()

        if month and year:
            filtered = []
            for c in contracts:
                for inst in c.installments:
                    if (inst.due_date and inst.due_date.month == month
                            and inst.due_date.year == year
                            and inst.status != 'cancelled'):
                        filtered.append(c)
                        break
            return [self._contract_summary(c) for c in filtered]

        return [self._contract_summary(c) for c in contracts]

    def _contract_summary(self, c):
        total = len(c.installments)
        paid = sum(1 for i in c.installments if i.status == 'paid')
        overdue = sum(
            1
            for i in c.installments
            if i.status in ('pending', 'partial') and i.due_date and i.due_date < datetime.utcnow().date()
        )
        pending_amount = sum(
            (i.amount - (i.paid_amount or 0)) for i in c.installments if i.status in ('pending', 'partial')
        )
        patient = User.query.get(c.patient_id) if c.patient_id else None

        return {
            'id': c.id,
            'patient_id': c.patient_id,
            'patient_name': patient.username if patient else '',
            'patient_email': patient.email if patient else '',
            'name': c.name,
            'total_amount': c.total_amount,
            'installment_count': total,
            'installment_amount': c.installment_amount,
            'paid_count': paid,
            'overdue_count': overdue,
            'status': c.status,
            'billing_type': c.billing_type or 'Mensual',
            'currency': c.currency or 'PEN',
            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else None,
            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else None,
            'notes': c.notes,
            'pending_amount': round(pending_amount, 2),
            'implementation_cost': c.implementation_cost or 0,
            'billing_rule': c.billing_rule or 'standard',
            'cancelled_at': c.cancelled_at.isoformat() if c.cancelled_at else None,
            'refund_status': c.refund_status,
            'total_refunded': c.total_refunded or 0,
        }

    def get_contract_detail(self, contract_id):
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
                    'paid_amount': inst.paid_amount or 0,
                    'paid_date': inst.paid_date.strftime('%Y-%m-%d %H:%M') if inst.paid_date else None,
                    'status': inst.status,
                    'reminder_sent': inst.reminder_sent,
                    'payment_id': inst.payment_id,
                    'payment_method': inst.payment_method,
                    'payment_notes': inst.payment_notes,
                    'is_free_month': inst.is_free_month,
                    'is_implementation': inst.is_implementation,
                    'description': inst.description,
                    'real_amount': inst.real_amount,
                    'refunded_amount': inst.refunded_amount or 0,
                }
            )

        patient = User.query.get(contract.patient_id) if contract.patient_id else None

        return {
            'id': contract.id,
            'patient_id': contract.patient_id,
            'patient_name': patient.username if patient else '',
            'patient_email': patient.email if patient else '',
            'name': contract.name,
            'total_amount': contract.total_amount,
            'installment_count': contract.installment_count,
            'installment_amount': contract.installment_amount,
            'start_date': contract.start_date.strftime('%Y-%m-%d') if contract.start_date else None,
            'end_date': contract.end_date.strftime('%Y-%m-%d') if contract.end_date else None,
            'status': contract.status,
            'notes': contract.notes,
            'billing_type': contract.billing_type or 'Mensual',
            'currency': contract.currency or 'PEN',
            'bonus_months': contract.bonus_months or 0,
            'sign_date': contract.sign_date.strftime('%Y-%m-%d') if contract.sign_date else None,
            'service_start_date': contract.service_start_date.strftime('%Y-%m-%d')
            if contract.service_start_date
            else None,
            'billing_rule': contract.billing_rule or 'standard',
            'implementation_cost': contract.implementation_cost or 0,
            'cancelled_at': contract.cancelled_at.isoformat() if contract.cancelled_at else None,
            'cancellation_reason': contract.cancellation_reason,
            'cancellation_comment': contract.cancellation_comment,
            'refund_status': contract.refund_status,
            'total_refunded': contract.total_refunded or 0,
            'installments': installments,
        }

    def pay_installment(
        self,
        installment_id,
        amount,
        method,
        reference=None,
        payment_date=None,
        discount=0.0,
        receipt_path=None,
        payment_notes=None,
        is_free_month=False,
    ):
        installment = Installment.query.get(installment_id)
        if not installment:
            return False, 'Cuota no encontrada'
        if installment.status == 'paid':
            return False, 'Esta cuota ya está pagada'

        try:
            payment_datetime = payment_date or datetime.utcnow()
            if isinstance(payment_datetime, str):
                payment_datetime = datetime.strptime(payment_datetime, '%Y-%m-%d')

            real_amount = 0 if is_free_month else float(amount)

            new_payment = None
            if real_amount > 0:
                new_payment = Payment(
                    patient_id=installment.contract.patient_id,
                    amount=real_amount,
                    method=method,
                    reference=reference,
                    receipt_image_path=receipt_path,
                    discount=discount,
                    date=payment_datetime,
                    installment_id=installment.id,
                )
                db.session.add(new_payment)
                db.session.flush()

            installment.paid_amount = (installment.paid_amount or 0) + real_amount
            installment.paid_date = payment_datetime
            installment.payment_method = 'Acuerdo comercial' if is_free_month else method
            installment.payment_notes = payment_notes
            installment.is_free_month = is_free_month
            installment.real_amount = real_amount

            if new_payment:
                installment.payment_id = new_payment.id

            total_paid = installment.paid_amount or 0

            if total_paid >= installment.amount:
                installment.status = 'paid'
            elif total_paid > 0:
                installment.status = 'partial'

            db.session.commit()
            return True, new_payment

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def cancel_contract(self, contract_id, cancellation_date=None, reason=None, comment=None, disposition='none'):
        contract = Contract.query.get(contract_id)
        if not contract:
            return False, 'Contrato no encontrado'
        if contract.status == 'cancelled':
            return False, 'El contrato ya está cancelado'

        try:
            cancel_dt = cancellation_date or datetime.utcnow()
            if isinstance(cancel_dt, str):
                cancel_dt = datetime.strptime(cancel_dt, '%Y-%m-%d')

            paid_amount = sum(i.paid_amount or 0 for i in contract.installments if i.status == 'paid')

            for inst in contract.installments:
                if inst.status in ('pending', 'partial'):
                    inst.status = 'cancelled'

            if disposition == 'refund':
                contract.total_refunded = paid_amount
                contract.refund_status = 'completed'
            elif disposition == 'credit':
                contract.total_refunded = paid_amount
                contract.refund_status = 'credit'

            contract.status = 'cancelled'
            contract.cancelled_at = cancel_dt
            contract.cancellation_reason = reason
            contract.cancellation_comment = comment

            db.session.commit()
            return True, contract

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def reactivate_contract(self, contract_id, reactivation_date=None, next_payment_date=None):
        contract = Contract.query.get(contract_id)
        if not contract:
            return False, 'Contrato no encontrado'
        if contract.status != 'cancelled':
            return False, 'Solo se pueden reactivar contratos cancelados'

        try:
            react_date = reactivation_date or datetime.utcnow().date()
            if isinstance(react_date, str):
                react_date = datetime.strptime(react_date, '%Y-%m-%d').date()

            next_pay = next_payment_date or react_date
            if isinstance(next_pay, str):
                next_pay = datetime.strptime(next_pay, '%Y-%m-%d').date()

            cancelled_installments = [i for i in contract.installments if i.status == 'cancelled']

            if cancelled_installments:
                new_dates = self._get_standard_due_dates(next_pay, len(cancelled_installments))
                for inst, new_date in zip(cancelled_installments, new_dates, strict=False):
                    inst.status = 'pending'
                    inst.due_date = new_date

            if contract.refund_status == 'credit' and contract.total_refunded > 0:
                credit = contract.total_refunded
                for inst in contract.installments:
                    if inst.status == 'pending' and credit > 0:
                        apply_amount = min(credit, inst.amount)
                        inst.paid_amount = (inst.paid_amount or 0) + apply_amount
                        inst.payment_method = 'Crédito por cancelación'
                        if inst.paid_amount >= inst.amount:
                            inst.status = 'paid'
                        else:
                            inst.status = 'partial'
                        credit -= apply_amount
                contract.refund_status = 'applied'

            contract.status = 'active'
            contract.cancelled_at = None
            contract.cancellation_reason = None
            contract.cancellation_comment = None

            db.session.commit()
            return True, contract

        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def get_due_installments(self, reference_date=None):
        if not reference_date:
            reference_date = datetime.utcnow().date()

        overdue = (
            Installment.query.filter(
                Installment.status.in_(['pending', 'partial']),
                Installment.due_date < reference_date,
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
                    'paid_amount': inst.paid_amount or 0,
                    'remaining': inst.amount - (inst.paid_amount or 0),
                    'days_overdue': days_overdue,
                    'number': inst.number,
                    'reminder_sent': inst.reminder_sent,
                }
            )
        return result

    def get_upcoming_installments(self, days_ahead=7):
        today = datetime.utcnow().date()
        limit_date = date.fromordinal(today.toordinal() + days_ahead)

        upcoming = (
            Installment.query.filter(
                Installment.status.in_(['pending', 'partial']),
                Installment.due_date >= today,
                Installment.due_date <= limit_date,
            )
            .order_by(Installment.due_date.asc())
            .all()
        )

        result = []
        for inst in upcoming:
            contract = Contract.query.get(inst.contract_id)
            patient = User.query.get(contract.patient_id) if contract else None
            result.append(
                {
                    'installment_id': inst.id,
                    'contract_id': inst.contract_id,
                    'patient_id': patient.id if patient else None,
                    'patient_name': patient.username if patient else '',
                    'due_date': inst.due_date.strftime('%Y-%m-%d'),
                    'amount': inst.amount,
                    'remaining': inst.amount - (inst.paid_amount or 0),
                    'number': inst.number,
                }
            )
        return result

    def get_debt_summary(self):
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

    def get_monthly_breakdown(self, month=None, year=None):
        today = datetime.utcnow().date()
        target_month = month or today.month
        target_year = year or today.year

        installments = (
            db.session.query(Installment)
            .join(Contract, Installment.contract_id == Contract.id)
            .filter(
                Contract.status == 'active',
                Installment.due_date.month == target_month,
                Installment.due_date.year == target_year,
            )
            .all()
        )

        total = len(installments)
        paid = sum(1 for i in installments if i.status == 'paid')
        pending = sum(1 for i in installments if i.status in ('pending', 'partial'))
        overdue = sum(1 for i in installments if i.status in ('pending', 'partial') and i.due_date < today)

        total_amount = sum(i.amount for i in installments)
        collected = sum(i.paid_amount or 0 for i in installments if i.status == 'paid')

        return {
            'month': target_month,
            'year': target_year,
            'total_installments': total,
            'paid': paid,
            'pending': pending,
            'overdue': overdue,
            'total_amount': round(total_amount, 2),
            'collected': round(collected, 2),
            'collection_rate': round((collected / total_amount * 100), 1) if total_amount > 0 else 0,
        }
