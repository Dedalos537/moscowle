from flask import jsonify, request

from app.auth_compat import login_required
from app.routes.admin import admin_bp
from app.services.contract_service import ContractService
from app.utils.decorators import admin_required

contract_service = ContractService()


@admin_bp.route('/api/contracts', methods=['GET'])
@login_required
@admin_required
def list_contracts():
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


@admin_bp.route('/api/contracts/<int:contract_id>', methods=['GET'])
@login_required
@admin_required
def get_contract(contract_id):
    detail = contract_service.get_contract_detail(contract_id)
    if not detail:
        return jsonify({'success': False, 'error': 'Contrato no encontrado'}), 404
    return jsonify({'success': True, 'contract': detail})


@admin_bp.route('/api/contracts', methods=['POST'])
@login_required
@admin_required
def create_contract():
    data = request.get_json(silent=True) or request.form.to_dict()
    patient_id = (
        data.get('patient_id', type=int) if isinstance(data.get('patient_id'), int) else int(data.get('patient_id', 0))
    )
    total_amount = (
        data.get('total_amount', type=float)
        if isinstance(data.get('total_amount'), float)
        else float(data.get('total_amount', 0))
    )

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
                'contract': {'id': result.id, 'name': result.name},
                'installments_generated': result.installment_count,
            }
        )
    return jsonify({'success': False, 'error': result}), 400


@admin_bp.route('/api/contracts/<int:contract_id>', methods=['PUT'])
@login_required
@admin_required
def update_contract(contract_id):
    from app.models import Contract, db

    contract = Contract.query.get(contract_id)
    if not contract:
        return jsonify({'success': False, 'error': 'Contrato no encontrado'}), 404

    data = request.get_json(silent=True) or {}
    allowed = {'name', 'notes', 'billing_type', 'currency', 'billing_rule'}
    for field in allowed:
        if field in data:
            setattr(contract, field, data[field])
    db.session.commit()
    return jsonify({'success': True, 'message': 'Contrato actualizado'})


@admin_bp.route('/api/contracts/<int:contract_id>/cancel', methods=['POST'])
@login_required
@admin_required
def cancel_contract(contract_id):
    data = request.get_json(silent=True) or {}
    reason = data.get('reason')
    if not reason:
        return jsonify({'success': False, 'error': 'reason requerido'}), 400

    success, result = contract_service.cancel_contract(
        contract_id=contract_id,
        cancellation_date=data.get('cancellation_date'),
        reason=reason,
        comment=data.get('comment'),
        disposition=data.get('disposition', 'none'),
    )
    if success:
        return jsonify({'success': True, 'message': 'Contrato cancelado'})
    return jsonify({'success': False, 'error': result}), 400


@admin_bp.route('/api/contracts/<int:contract_id>/reactivate', methods=['POST'])
@login_required
@admin_required
def reactivate_contract(contract_id):
    data = request.get_json(silent=True) or {}
    next_payment_date = data.get('next_payment_date')
    if not next_payment_date:
        return jsonify({'success': False, 'error': 'next_payment_date requerido'}), 400

    success, result = contract_service.reactivate_contract(
        contract_id=contract_id,
        reactivation_date=data.get('reactivation_date'),
        next_payment_date=next_payment_date,
    )
    if success:
        return jsonify({'success': True, 'message': 'Contrato reactivado'})
    return jsonify({'success': False, 'error': result}), 400


@admin_bp.route('/api/installments/<int:installment_id>/pay', methods=['POST'])
@login_required
@admin_required
def pay_installment(installment_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    amount = data.get('amount', type=float) if isinstance(data.get('amount'), float) else float(data.get('amount', 0))
    method = data.get('method', 'transfer')
    reference = data.get('reference')

    if not amount:
        return jsonify({'success': False, 'error': 'amount requerido'}), 400

    success, result = contract_service.pay_installment(
        installment_id,
        amount,
        method,
        reference=reference,
        payment_date=data.get('payment_date'),
        payment_notes=data.get('payment_notes'),
        is_free_month=data.get('is_free_month', False),
    )
    if success:
        return jsonify(
            {
                'success': True,
                'payment': {'id': result.id, 'amount': result.amount} if result else None,
                'message': 'Cuota pagada exitosamente',
            }
        )
    return jsonify({'success': False, 'error': result}), 400


@admin_bp.route('/api/installments/due', methods=['GET'])
@login_required
@admin_required
def due_installments():
    due = contract_service.get_due_installments()
    return jsonify({'success': True, 'installments': due})


@admin_bp.route('/api/installments/upcoming', methods=['GET'])
@login_required
@admin_required
def upcoming_installments():
    days = request.args.get('days', 7, type=int)
    upcoming = contract_service.get_upcoming_installments(days_ahead=days)
    return jsonify({'success': True, 'installments': upcoming})


@admin_bp.route('/api/debt-summary', methods=['GET'])
@login_required
@admin_required
def debt_summary():
    summary = contract_service.get_debt_summary()
    return jsonify({'success': True, 'debt_summary': summary})


@admin_bp.route('/api/contracts/monthly-breakdown', methods=['GET'])
@login_required
@admin_required
def monthly_breakdown():
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    breakdown = contract_service.get_monthly_breakdown(month=month, year=year)
    return jsonify({'success': True, 'data': breakdown})
