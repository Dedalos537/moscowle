from flask import Blueprint
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from app.services.finance_service import FinanceService
from app.services.workflow_engine import WorkflowEngine

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
dashboard_service = DashboardService()
payment_service = PaymentService()
finance_service = FinanceService()
workflow_engine = WorkflowEngine()

from . import users, payments, reports, sessions, misc
