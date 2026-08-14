from calendar import monthrange
from datetime import date, datetime

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
        guardian_name=None,
        guardian_dni=None,
        patient_dni=None,
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

        if guardian_name:
            patient.guardian_name = guardian_name
        if guardian_dni:
            patient.guardian_dni = guardian_dni
        if patient_dni:
            patient.document_number = patient_dni

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
                status=inst_data.get('status', 'pending'),
                description=inst_data.get('description'),
                is_implementation=inst_data.get('is_implementation', False),
                is_free_month=inst_data.get('is_free_month', False),
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
                    'is_free_month': False,
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
                    'is_free_month': False,
                }
            )
        elif billing_type == 'Semanal':
            from datetime import timedelta

            for i in range(duration):
                due = start_date + timedelta(weeks=i)
                is_free = i >= (duration - bonus) if bonus else False
                installments.append(
                    {
                        'number': i + 1,
                        'due_date': due,
                        'amount': 0.0 if is_free else price,
                        'status': 'free' if is_free else 'pending',
                        'description': f'Cuota Semanal {i + 1}' + (' (Bonificación)' if is_free else ''),
                        'is_implementation': False,
                        'is_free_month': is_free,
                    }
                )
        elif billing_type == 'Quincenal':
            from datetime import timedelta

            for i in range(duration):
                due = start_date + timedelta(days=14 * i)
                is_free = i >= (duration - bonus) if bonus else False
                installments.append(
                    {
                        'number': i + 1,
                        'due_date': due,
                        'amount': 0.0 if is_free else price,
                        'status': 'free' if is_free else 'pending',
                        'description': f'Cuota Quincenal {i + 1}' + (' (Bonificación)' if is_free else ''),
                        'is_implementation': False,
                        'is_free_month': is_free,
                    }
                )
        else:
            # Mensual (default)
            if billing_rule == 'sign-date':
                due_dates = self._get_sign_date_due_dates(sign_date, duration)
            else:
                due_dates = self._get_standard_due_dates(start_date, duration)

            for i in range(duration):
                is_free = i >= (duration - bonus) if bonus else False
                installments.append(
                    {
                        'number': i + 1,
                        'due_date': due_dates[i],
                        'amount': 0.0 if is_free else price,
                        'status': 'free' if is_free else 'pending',
                        'description': f'Cuota Mensual {i + 1}' + (' (Bonificación)' if is_free else ''),
                        'is_implementation': False,
                        'is_free_month': is_free,
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
        try:
            contracts = Contract.query.filter_by(patient_id=patient_id).order_by(Contract.created_at.desc()).all()
            return [self._contract_summary(c) for c in contracts]
        except Exception:
            return []

    def update_contract(self, contract_id, **kwargs):
        contract = Contract.query.get(contract_id)
        if not contract:
            return False, 'Contrato no encontrado'
        try:
            for key in ('name', 'notes', 'billing_type', 'currency', 'billing_rule'):
                if key in kwargs:
                    setattr(contract, key, kwargs[key])

            patient = User.query.get(contract.patient_id) if contract.patient_id else None
            if patient:
                for key in ('guardian_name', 'guardian_dni', 'guardian_contact', 'document_number'):
                    if key in kwargs and kwargs[key] is not None:
                        setattr(patient, key, kwargs[key])

            db.session.commit()
            return True, contract
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    def get_contracts_filtered(self, search=None, status=None, month=None, year=None, sede_id=None, limit=200):
        try:
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
                        if (
                            inst.due_date
                            and inst.due_date.month == month
                            and inst.due_date.year == year
                            and inst.status != 'cancelled'
                        ):
                            filtered.append(c)
                            break
                return [self._contract_summary(c) for c in filtered]

            return [self._contract_summary(c) for c in contracts]
        except Exception:
            return []

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
            'patient_dni': getattr(patient, 'document_number', None) if patient else None,
            'guardian_name': getattr(patient, 'guardian_name', None) if patient else None,
            'guardian_dni': getattr(patient, 'guardian_dni', None) if patient else None,
            'guardian_contact': getattr(patient, 'guardian_contact', None) if patient else None,
            'name': c.name,
            'total_amount': c.total_amount,
            'installment_count': total,
            'installment_amount': c.installment_amount,
            'paid_count': paid,
            'overdue_count': overdue,
            'status': c.status,
            'billing_type': getattr(c, 'billing_type', None) or 'Mensual',
            'currency': getattr(c, 'currency', None) or 'PEN',
            'start_date': c.start_date.strftime('%Y-%m-%d') if c.start_date else None,
            'end_date': c.end_date.strftime('%Y-%m-%d') if c.end_date else None,
            'notes': c.notes,
            'pending_amount': round(pending_amount, 2),
            'implementation_cost': getattr(c, 'implementation_cost', None) or 0,
            'billing_rule': getattr(c, 'billing_rule', None) or 'standard',
            'cancelled_at': getattr(c, 'cancelled_at', None).isoformat() if getattr(c, 'cancelled_at', None) else None,
            'refund_status': getattr(c, 'refund_status', None),
            'total_refunded': getattr(c, 'total_refunded', None) or 0,
        }

    @staticmethod
    def _installment_receipt_path(inst):
        """Return receipt_image_path from the Payment linked to an installment, if any."""
        if not inst.payment_id:
            return None
        payment = Payment.query.get(inst.payment_id)
        if not payment:
            return None
        return payment.receipt_image_path

    def get_contract_detail(self, contract_id):
        try:
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
                        'payment_method': getattr(inst, 'payment_method', None),
                        'payment_notes': getattr(inst, 'payment_notes', None),
                        'is_free_month': getattr(inst, 'is_free_month', False),
                        'is_implementation': getattr(inst, 'is_implementation', False),
                        'description': getattr(inst, 'description', None),
                        'real_amount': getattr(inst, 'real_amount', None),
                        'refunded_amount': getattr(inst, 'refunded_amount', None) or 0,
                        'receipt_image_path': self._installment_receipt_path(inst),
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
                'billing_type': getattr(contract, 'billing_type', None) or 'Mensual',
                'currency': getattr(contract, 'currency', None) or 'PEN',
                'bonus_months': getattr(contract, 'bonus_months', None) or 0,
                'sign_date': getattr(contract, 'sign_date', None).strftime('%Y-%m-%d')
                if getattr(contract, 'sign_date', None)
                else None,
                'service_start_date': getattr(contract, 'service_start_date', None).strftime('%Y-%m-%d')
                if getattr(contract, 'service_start_date', None)
                else None,
                'billing_rule': getattr(contract, 'billing_rule', None) or 'standard',
                'implementation_cost': getattr(contract, 'implementation_cost', None) or 0,
                'cancelled_at': getattr(contract, 'cancelled_at', None).isoformat()
                if getattr(contract, 'cancelled_at', None)
                else None,
                'cancellation_reason': getattr(contract, 'cancellation_reason', None),
                'cancellation_comment': getattr(contract, 'cancellation_comment', None),
                'refund_status': getattr(contract, 'refund_status', None),
                'total_refunded': getattr(contract, 'total_refunded', None) or 0,
                'installments': installments,
                'patient_dni': getattr(patient, 'document_number', None) if patient else None,
                'guardian_name': getattr(patient, 'guardian_name', None) if patient else None,
                'guardian_dni': getattr(patient, 'guardian_dni', None) if patient else None,
                'guardian_contact': getattr(patient, 'guardian_contact', None) if patient else None,
                'payment_plan': getattr(patient, 'payment_plan', None) if patient else None,
            }
        except Exception:
            return None

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
                    notes=payment_notes,
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
        try:
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
        except Exception:
            return []

    def get_upcoming_installments(self, days_ahead=7):
        try:
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
        except Exception:
            return []

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
