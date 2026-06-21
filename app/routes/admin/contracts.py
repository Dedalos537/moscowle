from flask import jsonify, request
from flask_login import login_required

from app.routes.admin import admin_bp
from app.services.contract_service import ContractService
from app.utils.decorators import admin_required

contract_service = ContractService()


@admin_bp.route('/api/contracts', methods=['GET'])
@login_required
@admin_required
def list_contracts():
    patient_id = request.args.get('patient_id', type=int)
    if not patient_id:
        return jsonify({'success': False, 'error': 'patient_id required'}), 400
    contracts = contract_service.get_patient_contracts(patient_id)
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
    patient_id = data.get('patient_id', type=int)
    total_amount = data.get('total_amount', type=float)
    installment_count = data.get('installment_count', 4, type=int)
    name = data.get('name')
    start_date = data.get('start_date')
    notes = data.get('notes')

    if not patient_id or not total_amount:
        return jsonify({'success': False, 'error': 'patient_id y total_amount requeridos'}), 400

    success, result = contract_service.create_contract(
        patient_id,
        total_amount,
        installment_count,
        name=name,
        start_date=start_date,
        notes=notes,
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


@admin_bp.route('/api/installments/<int:installment_id>/pay', methods=['POST'])
@login_required
@admin_required
def pay_installment(installment_id):
    data = request.get_json(silent=True) or request.form.to_dict()
    amount = data.get('amount', type=float)
    method = data.get('method', 'transfer')
    reference = data.get('reference')
    discount = data.get('discount', 0.0, type=float)

    if not amount:
        return jsonify({'success': False, 'error': 'amount requerido'}), 400

    success, result = contract_service.pay_installment(
        installment_id,
        amount,
        method,
        reference=reference,
        discount=discount,
    )
    if success:
        return jsonify(
            {
                'success': True,
                'payment': {'id': result.id, 'amount': result.amount},
            }
        )
    return jsonify({'success': False, 'error': result}), 400


@admin_bp.route('/api/installments/due', methods=['GET'])
@login_required
@admin_required
def due_installments():
    due = contract_service.get_due_installments()
    return jsonify({'success': True, 'installments': due})


@admin_bp.route('/api/debt-summary', methods=['GET'])
@login_required
@admin_required
def debt_summary():
    summary = contract_service.get_debt_summary()
    return jsonify({'success': True, 'debt_summary': summary})
