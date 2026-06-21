from flask import Blueprint

from app.services.dashboard_service import DashboardService
from app.services.financial_service import FinancialService
from app.services.payment_service import PaymentService
from app.services.workflow_engine import WorkflowEngine

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
dashboard_service = DashboardService()
payment_service = PaymentService()
finance_service = FinancialService()
workflow_engine = WorkflowEngine()

from . import contracts, misc, payments, reports, sessions, users
