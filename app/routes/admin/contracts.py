import logging

from flask import jsonify, request

from app.auth_compat import login_required
from app.routes.admin import admin_bp
from app.services.contract_service import ContractService
from app.utils.decorators import admin_required

logger = logging.getLogger(__name__)
contract_service = ContractService()


@admin_bp.route('/api/contracts', methods=['GET'])
@login_required
@admin_required
def list_contracts():
    try:
        search = request.args.get('search')
        status = request.args.get('status')
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        sede_id = request.args.get('sede_id', type=int)
        patient_id = request.args.get('patient_id', type=int)

        if patient_id:
            contracts = contract_service.get_patient_contracts(patient_id)
        else:
            contracts = contract_service.get_contracts_filtered(
                search=search,
                status=status,
                month=month,
                year=year,
                sede_id=sede_id,
            )
        return jsonify({'success': True, 'contracts': contracts})
    except Exception as e:
        logger.exception('Error listing contracts')
        return jsonify({'success': False, 'error': str(e), 'contracts': []}), 500


@admin_bp.route('/api/contracts/<int:contract_id>', methods=['GET'])
@login_required
@admin_required
def get_contract(contract_id):
    try:
        detail = contract_service.get_contract_detail(contract_id)
        if not detail:
            return jsonify({'success': False, 'error': 'Contrato no encontrado'}), 404
        return jsonify({'success': True, 'contract': detail})
    except Exception as e:
        logger.exception('Error getting contract detail')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/contracts', methods=['POST'])
@login_required
@admin_required
def create_contract():
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        patient_id = int(data.get('patient_id', 0))
        total_amount = float(data.get('total_amount', 0))

        if not patient_id or not total_amount:
            return jsonify({'success': False, 'error': 'patient_id y total_amount requeridos'}), 400

        success, result = contract_service.create_contract(
            patient_id=patient_id,
            total_amount=total_amount,
            installment_count=int(data.get('installment_count', 4)),
            name=data.get('name'),
            start_date=data.get('start_date'),
            notes=data.get('notes'),
            billing_type=data.get('billing_type', 'Mensual'),
            currency=data.get('currency', 'PEN'),
            bonus_months=int(data.get('bonus_months', 0)),
            billing_rule=data.get('billing_rule', 'standard'),
            implementation_cost=float(data.get('implementation_cost', 0)),
        )

        if success:
            return jsonify(
                {
                    'success': True,
                    'contract': {
                        'id': result.id,
                        'name': result.name,
                        'installment_count': result.installment_count,
                    },
                    'installments_generated': result.installment_count,
                }
            )
        return jsonify({'success': False, 'error': str(result)}), 400
    except Exception as e:
        logger.exception('Error creating contract')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/contracts/<int:contract_id>', methods=['PUT'])
@login_required
@admin_required
def update_contract(contract_id):
    try:
        data = request.get_json(silent=True) or {}
        success, result = contract_service.update_contract(contract_id, **data)
        if success:
            return jsonify({'success': True, 'message': 'Contrato actualizado'})
        return jsonify({'success': False, 'error': str(result)}), 400 if 'no encontrado' in str(result).lower() else 500
    except Exception as e:
        logger.exception('Error updating contract')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/contracts/<int:contract_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_contract(contract_id):
    try:
        data = request.get_json(silent=True) or {}
        reason = data.get('reason', '')
        if not reason:
            return jsonify({'success': False, 'error': 'Motivo de cancelación requerido'}), 400

        success, result = contract_service.cancel_contract(
            contract_id=contract_id,
            cancellation_date=data.get('cancellation_date'),
            reason=reason,
            comment=data.get('comment', ''),
            disposition=data.get('disposition', 'none'),
        )

        if success:
            return jsonify({'success': True, 'message': 'Contrato cancelado'})
        return jsonify({'success': False, 'error': str(result)}), 400
    except Exception as e:
        logger.exception('Error canceling contract')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/contracts/<int:contract_id>/reactivate', methods=['POST'])
@login_required
@admin_required
def reactivate_contract(contract_id):
    try:
        data = request.get_json(silent=True) or {}
        next_payment_date = data.get('next_payment_date')
        if not next_payment_date:
            return jsonify({'success': False, 'error': 'Fecha de próximo pago requerida'}), 400

        success, result = contract_service.reactivate_contract(
            contract_id=contract_id,
            reactivation_date=data.get('reactivation_date'),
            next_payment_date=next_payment_date,
        )

        if success:
            return jsonify({'success': True, 'message': 'Contrato reactivado'})
        return jsonify({'success': False, 'error': str(result)}), 400
    except Exception as e:
        logger.exception('Error reactivating contract')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/installments/<int:installment_id>/pay', methods=['POST'])
@login_required
@admin_required
def pay_installment(installment_id):
    try:
        data = request.get_json(silent=True) or {}
        amount = float(data.get('amount', 0))
        method = data.get('method', 'transfer')
        if not amount:
            return jsonify({'success': False, 'error': 'Monto requerido'}), 400

        success, result = contract_service.pay_installment(
            installment_id=installment_id,
            amount=amount,
            method=method,
            reference=data.get('reference', ''),
            payment_date=data.get('payment_date'),
            receipt_path=None,
            payment_notes=data.get('payment_notes', ''),
            is_free_month=data.get('is_free_month', False),
        )

        if success:
            return jsonify({'success': True, 'payment': {'id': result.id if result else None}})
        return jsonify({'success': False, 'error': str(result)}), 400
    except Exception as e:
        logger.exception('Error paying installment')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/installments/due', methods=['GET'])
@login_required
@admin_required
def due_installments():
    try:
        installments = contract_service.get_due_installments()
        return jsonify({'success': True, 'installments': installments})
    except Exception as e:
        logger.exception('Error getting due installments')
        return jsonify({'success': False, 'error': str(e), 'installments': []}), 500


@admin_bp.route('/api/installments/upcoming', methods=['GET'])
@login_required
@admin_required
def upcoming_installments():
    try:
        days = request.args.get('days', 7, type=int)
        installments = contract_service.get_upcoming_installments(days_ahead=days)
        return jsonify({'success': True, 'installments': installments})
    except Exception as e:
        logger.exception('Error getting upcoming installments')
        return jsonify({'success': False, 'error': str(e), 'installments': []}), 500


@admin_bp.route('/api/contracts/monthly-breakdown', methods=['GET'])
@login_required
@admin_required
def monthly_breakdown():
    try:
        month = request.args.get('month', type=int)
        year = request.args.get('year', type=int)
        breakdown = contract_service.get_monthly_breakdown(month=month, year=year)
        return jsonify({'success': True, 'data': breakdown})
    except Exception as e:
        logger.exception('Error getting monthly breakdown')
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/contracts/migrate-existing', methods=['POST'])
@login_required
@admin_required
def migrate_existing_patients():
    """Migrate patients with payment plans to Contract records."""
    try:
        from datetime import date, timedelta

        from app.extensions import db
        from app.models.user import User

        conn = db.session.connection()

        # First, ensure contract columns exist (in case migration hasn't run)
        contract_cols_to_add = [
            ('billing_type', "VARCHAR(20) DEFAULT 'Mensual'"),
            ('currency', "VARCHAR(5) DEFAULT 'PEN'"),
            ('bonus_months', 'INTEGER DEFAULT 0'),
            ('sign_date', 'DATE'),
            ('service_start_date', 'DATE'),
            ('billing_rule', "VARCHAR(20) DEFAULT 'standard'"),
            ('implementation_cost', 'FLOAT DEFAULT 0'),
            ('cancelled_at', 'DATETIME'),
            ('cancellation_reason', 'VARCHAR(200)'),
            ('cancellation_comment', 'TEXT'),
            ('refund_status', 'VARCHAR(20)'),
            ('total_refunded', 'FLOAT DEFAULT 0'),
        ]
        for col_name, col_def in contract_cols_to_add:
            try:
                conn.execute(db.text(f'ALTER TABLE contract ADD COLUMN {col_name} {col_def}'))
            except Exception:
                pass  # Column already exists

        installment_cols_to_add = [
            ('real_amount', 'FLOAT'),
            ('payment_method', 'VARCHAR(50)'),
            ('payment_currency', 'VARCHAR(5)'),
            ('payment_notes', 'TEXT'),
            ('is_free_month', 'BOOLEAN DEFAULT 0'),
            ('refunded_amount', 'FLOAT DEFAULT 0'),
            ('refunded_at', 'DATETIME'),
            ('description', 'VARCHAR(200)'),
            ('is_implementation', 'BOOLEAN DEFAULT 0'),
        ]
        for col_name, col_def in installment_cols_to_add:
            try:
                conn.execute(db.text(f'ALTER TABLE installment ADD COLUMN {col_name} {col_def}'))
            except Exception:
                pass  # Column already exists

        db.session.commit()
        conn = db.session.connection()

        # Now migrate patients to contracts using raw SQL
        patients = User.query.filter(
            User.role == 'jugador',
            User.is_active == True,
            User.payment_amount > 0,
        ).all()

        created = 0
        skipped = 0
        errors = []

        for patient in patients:
            try:
                existing = conn.execute(
                    db.text("SELECT id FROM contract WHERE patient_id = :pid AND status = 'active'"),
                    {'pid': patient.id},
                ).fetchone()
                if existing:
                    skipped += 1
                    continue

                billing_type = 'Mensual'
                if patient.payment_plan:
                    plan_map = {
                        'weekly': 'Semanal',
                        'biweekly': 'Quincenal',
                        'monthly': 'Mensual',
                        'annual': 'Anual',
                    }
                    billing_type = plan_map.get(patient.payment_plan, 'Mensual')

                installment_count = 12
                if billing_type == 'Semanal':
                    installment_count = 48
                elif billing_type == 'Quincenal':
                    installment_count = 24
                elif billing_type == 'Anual':
                    installment_count = 1

                total_amount = patient.payment_amount * installment_count

                # Use earliest payment date as start_date (so past payments match installments)
                earliest_pay = conn.execute(
                    db.text('SELECT MIN(date) as min_date FROM payment WHERE patient_id = :pid'),
                    {'pid': patient.id},
                ).fetchone()
                if earliest_pay and earliest_pay.min_date:
                    raw_date = earliest_pay.min_date
                    if hasattr(raw_date, 'date'):
                        raw_date = raw_date.date()
                    start_date = date(raw_date.year, raw_date.month, 1)
                else:
                    start_date = patient.payment_due_date or date.today()

                # Ensure installment_count covers from start_date to today + 1 month
                today = date.today()
                months_needed = (today.year - start_date.year) * 12 + (today.month - start_date.month) + 1
                if installment_count < months_needed:
                    installment_count = months_needed
                    total_amount = patient.payment_amount * installment_count

                result = conn.execute(
                    db.text("""
                        INSERT INTO contract (patient_id, name, total_amount, installment_count,
                            installment_amount, start_date, status, billing_type, currency, billing_rule,
                            created_at, updated_at)
                        VALUES (:pid, :name, :total, :icount, :iamount, :start, 'active',
                            :btype, 'PEN', 'standard', NOW(), NOW())
                    """),
                    {
                        'pid': patient.id,
                        'name': f'Plan {billing_type} - {patient.username}',
                        'total': round(total_amount, 2),
                        'icount': installment_count,
                        'iamount': round(patient.payment_amount, 2),
                        'start': start_date,
                        'btype': billing_type,
                    },
                )
                contract_id = result.lastrowid

                if billing_type == 'Semanal':
                    for i in range(installment_count):
                        due = start_date + timedelta(weeks=i)
                        conn.execute(
                            db.text("""
                                INSERT INTO installment (contract_id, number, due_date, amount, status,
                                    description, is_free_month, is_implementation, created_at, updated_at)
                                VALUES (:cid, :num, :due, :amt, 'pending', :desc, 0, 0, NOW(), NOW())
                            """),
                            {
                                'cid': contract_id,
                                'num': i + 1,
                                'due': due,
                                'amt': round(patient.payment_amount, 2),
                                'desc': f'Cuota Semanal {i + 1}',
                            },
                        )
                elif billing_type == 'Quincenal':
                    for i in range(installment_count):
                        due = start_date + timedelta(days=14 * i)
                        conn.execute(
                            db.text("""
                                INSERT INTO installment (contract_id, number, due_date, amount, status,
                                    description, is_free_month, is_implementation, created_at, updated_at)
                                VALUES (:cid, :num, :due, :amt, 'pending', :desc, 0, 0, NOW(), NOW())
                            """),
                            {
                                'cid': contract_id,
                                'num': i + 1,
                                'due': due,
                                'amt': round(patient.payment_amount, 2),
                                'desc': f'Cuota Quincenal {i + 1}',
                            },
                        )
                else:
                    for i in range(installment_count):
                        m = start_date.month + i
                        y = start_date.year + (m - 1) // 12
                        m = (m - 1) % 12 + 1
                        last_day = 30 if m in (4, 6, 9, 11) else (29 if m == 2 and y % 4 == 0 else 28) if m == 2 else 31
                        day = min(start_date.day, last_day)
                        due = date(y, m, day)
                        conn.execute(
                            db.text("""
                                INSERT INTO installment (contract_id, number, due_date, amount, status,
                                    description, is_free_month, is_implementation, created_at, updated_at)
                                VALUES (:cid, :num, :due, :amt, 'pending', :desc, 0, 0, NOW(), NOW())
                            """),
                            {
                                'cid': contract_id,
                                'num': i + 1,
                                'due': due,
                                'amt': round(patient.payment_amount, 2),
                                'desc': f'Cuota Mensual {i + 1}',
                            },
                        )

                # Link existing Payment records to installments
                try:
                    payments = conn.execute(
                        db.text(
                            'SELECT id, amount, method, date, notes FROM payment '
                            'WHERE patient_id = :pid AND installment_id IS NULL ORDER BY date ASC'
                        ),
                        {'pid': patient.id},
                    ).fetchall()

                    if payments:
                        # Get installments for this contract ordered by due_date
                        installments = conn.execute(
                            db.text(
                                'SELECT id, due_date, amount, status FROM installment '
                                "WHERE contract_id = :cid AND status = 'pending' ORDER BY due_date ASC"
                            ),
                            {'cid': contract_id},
                        ).fetchall()

                        # Build month->installment map
                        inst_map = {}
                        for inst in installments:
                            if inst.due_date:
                                key = (inst.due_date.year, inst.due_date.month)
                                if key not in inst_map:
                                    inst_map[key] = inst

                        linked = 0
                        for pay in payments:
                            pay_date = pay.date
                            if hasattr(pay_date, 'date'):
                                pay_date = pay_date.date()
                            key = (pay_date.year, pay_date.month)
                            inst = inst_map.get(key)
                            if inst:
                                conn.execute(
                                    db.text(
                                        "UPDATE installment SET status='paid', paid_amount=:amt, "
                                        'paid_date=:pdate, payment_id=:payid, '
                                        'payment_method=:pmeth, updated_at=NOW() '
                                        'WHERE id=:iid'
                                    ),
                                    {
                                        'amt': float(pay.amount),
                                        'pdate': pay.date,
                                        'payid': pay.id,
                                        'pmeth': pay.method or 'Efectivo',
                                        'iid': inst.id,
                                    },
                                )
                                # Also back-link the Payment to the installment
                                conn.execute(
                                    db.text('UPDATE payment SET installment_id=:iid WHERE id=:payid'),
                                    {'iid': inst.id, 'payid': pay.id},
                                )
                                # Remove from map so it's not matched again
                                del inst_map[key]
                                linked += 1

                except Exception:
                    pass  # Best effort — don't break migration if linking fails

                created += 1
            except Exception as e:
                errors.append(f'Patient {patient.id}: {str(e)}')
                db.session.rollback()
                continue

        db.session.commit()

        return jsonify(
            {
                'success': True,
                'created': created,
                'skipped': skipped,
                'errors': errors,
                'total_patients': len(patients),
            }
        )
    except Exception as e:
        logger.exception('Error migrating existing patients')
        return jsonify({'success': False, 'error': str(e)}), 500
