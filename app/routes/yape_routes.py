
from flask import Blueprint, request, jsonify, current_app, render_template
from app.auth_compat import login_required
import logging

from app.models import YapeTransaction, db
from app.services.yape_service import YapeService
from app.utils.decorators import admin_required

logger = logging.getLogger(__name__)

yape_bp = Blueprint('yape', __name__, url_prefix='/admin/yape')
yape_service = YapeService()


@yape_bp.route('/import', methods=['GET', 'POST'])
@login_required
@admin_required
def import_transactions():
    """Import Yape CSV or XLSX file."""
    if request.method == 'GET':
        return render_template('admin/yape_import.html'), 200
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'Empty file'}), 400
        
        ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'csv'
        file_type = 'xlsx' if ext in ['xlsx', 'xls'] else 'csv'
        
        success, result = yape_service.import_transactions(file, file_type=file_type)
        
        if success:
            return jsonify({'success': True, 'stats': result}), 200
        return jsonify({'success': False, 'error': result}), 400
    except Exception as e:
        logger.exception("Import error")
        return jsonify({'success': False, 'error': str(e)}), 500


@yape_bp.route('/search', methods=['GET'])
@login_required
@admin_required
def search():
    """Search Yape transactions."""
    try:
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'results': []}), 200
        
        results = yape_service.search_transactions(q, limit=20)
        return jsonify({'results': [{'operation_number': r.operation_number, 'amount': r.amount, 'sender': r.sender_name} for r in results]}), 200
    except Exception as e:
        logger.exception("Search error")
        return jsonify({'error': str(e)}), 500


@yape_bp.route('/<operation_number>/attach-receipt', methods=['POST'])
@login_required
@admin_required
def attach_receipt(operation_number):
    """Attach receipt image to transaction."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file'}), 400
        
        file = request.files['file']
        receipt_path = f"yape_receipts/{operation_number}_{file.filename}"
        
        success, msg = yape_service.attach_receipt_to_transaction(operation_number, receipt_path)
        return jsonify({'success': success, 'message': msg}), (200 if success else 400)
    except Exception as e:
        logger.exception("Attach error")
        return jsonify({'success': False, 'error': str(e)}), 500


@yape_bp.route('/pending', methods=['GET'])
@login_required
@admin_required
def pending():
    """Get pending transactions without receipt."""
    try:
        pending_tx = YapeTransaction.query.filter(YapeTransaction.receipt_image_path == None).limit(50).all()
        return jsonify({'count': len(pending_tx), 'transactions': [{'operation_number': t.operation_number, 'amount': t.amount} for t in pending_tx]}), 200
    except Exception as e:
        logger.exception("Pending error")
        return jsonify({'error': str(e)}), 500


@yape_bp.route('/history', methods=['GET'])
@login_required
@admin_required
def history():
    """Get import history."""
    try:
        imports = yape_service.get_all_imports()
        return jsonify({'count': len(imports), 'imports': imports}), 200
    except Exception as e:
        logger.exception("History error")
        return jsonify({'error': str(e)}), 500


@yape_bp.route('/dashboard', methods=['GET'])
@login_required
@admin_required
def dash():
    """Yape dashboard stats."""
    try:
        total = YapeTransaction.query.count()
        pending_count = YapeTransaction.query.filter(YapeTransaction.receipt_image_path == None).count()
        return jsonify({'total': total, 'pending': pending_count}), 200
    except Exception as e:
        logger.exception("Dashboard error")
        return jsonify({'error': str(e)}), 500
