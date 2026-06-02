from app.services.receipt_generator import generate_receipt_pdf
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request, jsonify, send_file
from flask_login import login_required, current_user
from functools import wraps
import os
from datetime import timedelta
from app.extensions import bcrypt, db, csrf
from app.services.availability_service import AvailabilityService
from app.models import AdminAPIToken
import secrets
from app.services.availability_service import AvailabilityService
from app.models import User, Appointment, SessionMetrics, db, Payment, CSPReport, Sede, ContactMessage, SmartAction
from app.services.dashboard_service import DashboardService
from app.services.payment_service import PaymentService
from app.services.finance_service import FinanceService
from sqlalchemy import func
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime
import json
from app.schemas.payment_schema import validate_payment_register

from app.services.workflow_engine import WorkflowEngine

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
dashboard_service = DashboardService()
payment_service = PaymentService()
finance_service = FinanceService()
workflow_engine = WorkflowEngine()


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Trigger workflow update (Phase 1: Background scan)
    try:
        WorkflowEngine().generate_daily_actions()
    except Exception as e:
        current_app.logger.error(f"Workflow Engine Scan Error: {str(e)}")

    try:
        overview = dashboard_service.get_admin_overview()
    except Exception as e:
        current_app.logger.error(f"Dashboard Service Overview Error: {str(e)}")
        overview = {'therapists': 0, 'patients': 0, 'sessions_total': 0, 'avg_accuracy': 0}
    
    # NEW: Fetch smart actions for the dashboard
    try:
        smart_actions = SmartAction.query.filter_by(status='pending').order_by(SmartAction.created_at.desc()).limit(10).all()
    except Exception as e:
        current_app.logger.error(f"Fetch Smart Actions Error: {str(e)}")
        smart_actions = []
    
    # NEW: Financial Summary
    try:
        financials = payment_service.get_financial_summary()
    except Exception as e:
        current_app.logger.error(f"Payment Service Financial Summary Error: {str(e)}")
        financials = {'income_real': 0, 'income_expected': 0}
        
    # NEW: Sedes Breakdown
    sedes_stats = []
    try:
        sedes = Sede.query.filter_by(active=True).order_by(Sede.name.asc()).all()
        for s in sedes:
            count = User.query.filter_by(sede_id=s.id, role='jugador', is_active=True).count()
            sedes_stats.append({'id': s.id, 'name': s.name, 'count': count})
    except Exception as e:
        current_app.logger.error(f"Sedes Breakdown Error: {str(e)}")
        
    # All active patients for the "Quick Pay" dropdown
    try:
        all_patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    except Exception as e:
        current_app.logger.error(f"Fetch All Patients Error: {str(e)}")
        all_patients = []
    
    return render_template('admin/dashboard.html', 
                           overview=overview, 
                           financials=financials,
                           sedes_stats=sedes_stats,
                           all_patients=all_patients,
                           smart_actions=smart_actions, 
                           active_page='admin_dashboard')

@admin_bp.route('/api/workflow/execute/<int:action_id>', methods=['POST'])
@login_required
def execute_smart_action(action_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'message': 'Acceso denegado.'}), 403
        
    action = SmartAction.query.get_or_404(action_id)
    if action.status != 'pending':
        return jsonify({'success': False, 'message': 'Acción ya procesada.'}), 400
        
    payload = action.get_payload()
    action_type = payload.get('action')
    
    try:
        # EXECUTION DISPATCHER (The heart of automation)
        if action_type == 'complete_session':
            appt = Appointment.query.get(payload['appointment_id'])
            if appt:
                appt.status = 'completed'
                appt.attendance = 'present'
                if appt.patient:
                    appt.patient.sessions_attended += 1
        
        elif action_type == 'request_payment':
            # This would integrate with notification service
            pass # Phase 1: Just mark as resolved after manual confirmation
            
        # Generic resolution
        action.status = 'resolved'
        action.resolved_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'message': f'Acción {action_id} ejecutada, dale.'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/users')
@login_required
def users():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    sede_filter = request.args.get('sede_id')
    query = User.query
    
    if sede_filter and sede_filter.isdigit():
        query = query.filter(User.sede_id == int(sede_filter))
        
    users = query.order_by(User.created_at.desc()).all()
    
    # Pre-fetch therapist assignments for template
    patient_therapist_map = {}
    for u in users:
        if u.role == 'jugador':
            # Use the dynamic relationship to fetch IDs
            # u.therapists is a query object
            patient_therapist_map[u.id] = [t.id for t in u.therapists]
            
    therapists = User.query.filter_by(role='terapista').order_by(User.username.asc()).all()
    sedes = Sede.query.filter_by(active=True).order_by(Sede.name.asc()).all()
    
    return render_template('admin/users.html', users=users, therapists=therapists, patient_therapist_map=patient_therapist_map, sedes=sedes, active_page='admin_users')

@admin_bp.route('/users/<int:user_id>')
@login_required
def user_details(user_id):
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Gather comprehensive stats for this user
    stats = {}
    
    if user.role == 'jugador':
        stats['total_sessions'] = SessionMetrics.query.filter_by(user_id=user.id).count()
        stats['last_session'] = SessionMetrics.query.filter_by(user_id=user.id).order_by(SessionMetrics.date.desc()).first()
        stats['payments_count'] = Payment.query.filter_by(patient_id=user.id).count()
        stats['assigned_therapists'] = user.therapists.all()
        # Calculate payment status
        # This logic could be moved to a service, but keeping it simple here for now
        stats['sessions_left'] = user.sessions_total - user.sessions_attended
    
    elif user.role == 'terapista':
        stats['assigned_sedes'] = user.assigned_sedes.all()
        # Count active patients assigned to this therapist using the backref from User.therapists
        stats['active_patients_count'] = user.associated_patients.filter_by(is_active=True).count()
        
    return render_template('admin/user_detail.html', user=user, stats=stats, active_page='admin_users')

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes cambiar tu propio estado.', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))
    
    status = request.form.get('status') or 'active'
    
    if status not in ['active', 'inactive', 'retired', 'debtor']:
        flash('Estado inválido', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))
    
    user.account_status = status
    
    user.is_active = (status == 'active')
    
    messages = {
        'active': 'Usuario activado, todo ok',
        'inactive': 'Usuario desactivado',
        'retired': 'Usuario marcado como retirado',
        'debtor': 'Usuario marcado como deudor'
    }
    
    db.session.commit()
    flash(messages.get(status, 'Estado actualizado'), 'success')
    return redirect(url_for('admin.user_details', user_id=user.id))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
        
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))
    
    # Check for related records logic could be here
    # For now, simplistic delete (assuming cascade or handling via integrity error)
    try:
        db.session.delete(user)
        db.session.commit()
        flash('Usuario eliminado, listo.', 'success')
        return redirect(url_for('admin.users'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar usuario: {str(e)}', 'error')
        return redirect(url_for('admin.user_details', user_id=user.id))

@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
        
    user = User.query.get_or_404(user_id)
    flash(f'Correo de restablecimiento enviado a {user.email} (simulado)', 'success')
    return redirect(url_for('admin.user_details', user_id=user.id))

@admin_bp.route('/games')
@login_required
def games():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    games_dir = os.path.join(current_app.root_path, 'static', 'games')
    try:
        files = [f for f in os.listdir(games_dir) if f.lower().endswith('.html')]
    except Exception:
        files = []
    return render_template('admin/games.html', games=files, active_page='admin_games')

@admin_bp.route('/reports')
@login_required
def reports():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Aggregate simple stats per therapist and patient
        therapists = User.query.filter_by(role='terapista').all()
        t_rows = []
        for t in therapists:
            count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
            # Calculate average accuracy for sessions managed by this therapist
            # Using try/except within loop to prevent one bad record from crashing all
            try:
                avg_acc = db.session.query(func.avg(SessionMetrics.accurracy))\
                    .join(Appointment, SessionMetrics.session_id == Appointment.id)\
                    .filter(Appointment.therapist_id == t.id).scalar() or 0
            except Exception:
                avg_acc = 0
            t_rows.append({'name': t.username, 'email': t.email, 'sessions': count_appts, 'avg_accuracy': round(avg_acc,1)})
        
        patients = User.query.filter_by(role='jugador').all()
        p_rows = []
        for p in patients:
            plays = SessionMetrics.query.filter_by(user_id=p.id).count()
            try:
                acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
            except Exception:
                acc = 0
            p_rows.append({'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc,1)})
        
        # Financial Stats (Ticket 5)
        try:
            financials = payment_service.get_financial_summary()
        except Exception as e:
            current_app.logger.warning(f"Failed to load financials: {e}")
            financials = {
                'income_real': 0.0,
                'income_expected': 0.0, 
                'overdue_amount': 0.0,
                'overdue_users_count': 0,
                'expenses': 0.0,
                'net_profit': 0.0
            }
        
        # Audit Stats (HU-06 / HU-08)
        try:
            from app.models import SessionAudit
            from sqlalchemy import func as sqlfunc
            
            total_audits = SessionAudit.query.filter(SessionAudit.audit_score.isnot(None)).count()
            avg_score = db.session.query(sqlfunc.avg(SessionAudit.audit_score)).filter(
                SessionAudit.audit_score.isnot(None)
            ).scalar() or 0
            
            # Recent audits with session info
            recent_audits = db.session.query(
                SessionAudit, Appointment, User
            ).join(
                Appointment, SessionAudit.appointment_id == Appointment.id
            ).join(
                User, Appointment.therapist_id == User.id
            ).filter(
                SessionAudit.audit_score.isnot(None)
            ).order_by(SessionAudit.audited_at.desc()).limit(20).all()
            
            audit_rows = []
            for audit, appt, therapist in recent_audits:
                patient = User.query.get(appt.patient_id)
                audit_rows.append({
                    'id': audit.id,
                    'therapist': therapist.username,
                    'patient': patient.username if patient else 'N/A',
                    'date': appt.start_time.strftime('%d/%m/%Y') if appt.start_time else 'N/A',
                    'score': round(audit.audit_score, 1) if audit.audit_score else 0,
                    'status': audit.audit_status
                })
            
            # Scores by therapist
            therapist_scores = db.session.query(
                User.username,
                sqlfunc.avg(SessionAudit.audit_score).label('avg_score'),
                sqlfunc.count(SessionAudit.id).label('count')
            ).join(
                Appointment, SessionAudit.appointment_id == Appointment.id
            ).join(
                User, Appointment.therapist_id == User.id
            ).filter(
                SessionAudit.audit_score.isnot(None)
            ).group_by(User.id).all()
            
            audit_stats = {
                'total': total_audits,
                'avg_score': round(avg_score, 1),
                'recent': audit_rows,
                'by_therapist': [{'name': t[0], 'avg_score': round(t[1], 1), 'count': t[2]} for t in therapist_scores]
            }
        except Exception as e:
            current_app.logger.warning(f"Failed to load audit stats: {e}")
            audit_stats = {'total': 0, 'avg_score': 0, 'recent': [], 'by_therapist': []}
        
        return render_template('admin/reports.html', 
                               therapists=t_rows, 
                               patients=p_rows, 
                               financials=financials,
                               audit_stats=audit_stats,
                               active_page='admin_reports')
    except Exception as e:
        current_app.logger.error(f"Error in admin/reports: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error generando reportes: {str(e)}", 'error')
        return render_template('admin/reports.html', therapists=[], patients=[], financials={'income_real':0,'income_expected':0,'overdue_amount':0,'overdue_users_count':0}, active_page='admin_reports')

@admin_bp.route('/generate-ia-report', methods=['POST'])
@login_required
def generate_ia_report():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        from app.services.llm_automation_service import generate_weekly_report, process_chat_command
        from app.services.financial_service import FinancialService
        from datetime import datetime, timedelta
        from sqlalchemy import func
        
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        first_of_month = now.replace(day=1)
        
        total_therapists = User.query.filter_by(role='terapista', is_active=True).count()
        total_patients = User.query.filter_by(role='jugador', is_active=True).count()
        total_sessions = Appointment.query.filter(Appointment.status == 'completed').count()
        sessions_this_month = Appointment.query.filter(
            Appointment.status == 'completed',
            Appointment.updated_at >= first_of_month
        ).count()
        
        # Financial data
        recent_payments = Payment.query.filter(Payment.date >= thirty_days_ago).all()
        total_income = sum((p.amount or 0) - (p.discount or 0) for p in recent_payments)
        
        total_expenses = 0
        try:
            from app.models import Expense
            recent_expenses = Expense.query.filter(Expense.date >= thirty_days_ago).all()
            total_expenses = sum((e.amount or 0) for e in recent_expenses)
        except ImportError:
            pass
        
        # Debt report
        fs = FinancialService()
        debt_data = fs.build_debt_report(days_ahead=7, month='all')
        total_debt = debt_data.get('total_deuda', 0)
        total_debtors = debt_data.get('total_pacientes', 0)
        
        # Top therapists by session count
        top_therapists = db.session.query(
            User.username,
            func.count(Appointment.id).label('session_count')
        ).join(Appointment, Appointment.therapist_id == User.id)\
         .filter(Appointment.status == 'completed')\
         .group_by(User.id)\
         .order_by(func.count(Appointment.id).desc())\
         .limit(5).all()
        
        # Recent session notes
        sessions = Appointment.query.filter(Appointment.status == 'completed')\
            .order_by(Appointment.updated_at.desc()).limit(10).all()
        session_data = [{
            "notes": s.notes,
            "patient": s.patient.username if s.patient else '—',
            "therapist": s.therapist.username if s.therapist else '—'
        } for s in sessions if s.notes]
        
        data_for_ai = {
            "period": f"Reporte Estratégico {now.strftime('%d/%m/%Y')}",
            "general": {
                "therapists": total_therapists,
                "patients": total_patients,
                "total_sessions": total_sessions,
                "sessions_this_month": sessions_this_month,
            },
            "financial": {
                "total_debt": total_debt,
                "total_debtors": total_debtors,
                "income_last_30d": total_income,
                "total_expenses": total_expenses,
            },
            "top_therapists": [{"name": t.username, "sessions": t.session_count} for t in top_therapists],
            "recent_session_notes": session_data,
        }
        
        try:
            report_md = generate_weekly_report(data_for_ai)
        except Exception as llm_err:
            current_app.logger.warning(f"LLM report generation failed, using fallback: {llm_err}")
            report_md = (
                f"# Reporte Estrategico - {now.strftime('%d/%m/%Y')}\n\n"
                f"## Resumen General\n"
                f"- Terapeutas activos: {total_therapists}\n"
                f"- Pacientes activos: {total_patients}\n"
                f"- Sesiones totales: {total_sessions}\n"
                f"- Sesiones este mes: {sessions_this_month}\n\n"
                f"## Financiero\n"
                f"- Ingresos (30 dias): S/ {total_income:.2f}\n"
                f"- Gastos (30 dias): S/ {total_expenses:.2f}\n"
                f"- Deuda total: S/ {total_debt:.2f}\n"
                f"- Deudores: {total_debtors}\n\n"
                f"## Top Terapeutas\n"
            )
            for t in top_therapists:
                report_md += f"- {t.username}: {t.session_count} sesiones\n"
            if session_data:
                report_md += f"\n## Notas de Sesiones Recientes\n"
                for s in session_data:
                    report_md += f"- {s['patient']} ({s['therapist']}): {s['notes'][:100]}...\n"
        return jsonify({'success': True, 'report': report_md})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@admin_bp.route('/ai-chat-process', methods=['POST'])
@login_required
def ai_chat_process():
    """Chatbot Llama"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    # 1. Manejo de Subida de Vouchers (OCR Local Local local)
    if 'file' in request.files:
        file = request.files['file']
        if file:
            filename = secure_filename(f"chat_vc_{uuid.uuid4().hex}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts', filename)
            os.makedirs(os.path.dirname(upload_path), exist_ok=True)
            file.save(upload_path)
            
            try:
                from app.services.llm_automation_service import analyze_receipt_image
                ocr_out = analyze_receipt_image(upload_path)
                p = User.query.filter(User.username.ilike(f"%{ocr_out.get('sender_name', '')}%"), User.role == 'jugador').first()
                
                msg = f"Leído: S/ {ocr_out.get('amount')} de {ocr_out.get('sender_name')}.\n"
                if p:
                    msg += f"Es {p.username}. ¿Confirmamos?"
                    return jsonify({'response': msg, 'status': 'success', 'action': 'confirm_payment', 'params': {'patient_id': p.id, 'amount': ocr_out.get('amount'), 'path': upload_path}})
                return jsonify({'response': msg + "¿De qué paciente es?", 'status': 'info'})
            except:
                return jsonify({'response': "No entendí el voucher, ¿me dictas?", 'status': 'warning'})

    # 2. Análisis con Llama Central
    data = request.get_json() or {}
    msg_user = data.get('message', '')
    context = {'page': request.referrer or 'dashboard'}
    
    try:
        from app.services.llm_automation_service import process_chat_command
        from app.services.notification_service import NotificationService
        notif_service = NotificationService()
        
        result = process_chat_command(current_user.id, msg_user, context)
        
        intent = result.get('intent', 'general_chat')
        params = result.get('parameters', {})
        friendly = result.get('friendly_response', "¡Claro que sí! ")
        
        # DISPATCHER DE ACCIONES LIMPIO
        if intent == 'register_payment':
            p_name = params.get('patient_name')
            amt = params.get('amount')
            if not p_name or not amt:
                return jsonify({'response': friendly, 'status': 'info'}) 
            
            p = User.query.filter(User.username.ilike(f"%{p_name}%"), User.role == 'jugador').first()
            if not p: return jsonify({'response': f"No encontré a {p_name}.", 'status': 'warning'})
            
            payment_service.register_payment(patient_id=p.id, amount=float(amt), method='IA/Llama', reference='Chatbot', next_due_date_str=(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'))
            
            # Notificación de Llama
            notif_service.create_notification(
                current_user.id, 
                f" Llama: Registré pago de S/ {amt} para {p.username}.",
                url_for('admin.payment_history', user_id=p.id)
            )
            return jsonify({'response': friendly, 'status': 'success', 'redirect': url_for('admin.payment_history', user_id=p.id)})

        elif intent == 'register_expense':
            amt = params.get('amount')
            desc = params.get('description', 'Gasto vía Llama')
            cat = params.get('category', 'operativo')
            if not amt: return jsonify({'response': friendly, 'status': 'info'})
            
            finance_service.create_expense({'category': cat, 'amount': float(amt), 'date': datetime.now().strftime('%Y-%m-%d'), 'description': desc, 'method': 'IA/Chat'})
            
            # Notificación de Llama
            notif_service.create_notification(
                current_user.id, 
                f" Llama: Registré un nuevo gasto de S/ {amt} ({cat}).",
                url_for('admin.expenses')
            )
            return jsonify({'response': friendly, 'status': 'success', 'redirect': url_for('admin.expenses')})

        elif intent == 'mark_attendance':
            p_name = params.get('patient_name')
            p = User.query.filter(User.username.ilike(f"%{p_name}%")).first()
            if p:
                apt = Appointment.query.filter_by(patient_id=p.id, status='scheduled').filter(func.date(Appointment.start_time) == datetime.now().date()).first()
                if apt:
                    apt.status = 'completed'; db.session.commit()
                    notif_service.create_notification(
                        current_user.id, 
                        f" Llama: Marqué asistencia para {p.username}.",
                        url_for('admin.sessions_page')
                    )
                    return jsonify({'response': friendly, 'status': 'success'})
            return jsonify({'response': f"No hay citas hoy de {p_name}.", 'status': 'warning'})

        elif intent == 'navigate':
            dest = params.get('destination', '').lower()
            target_url = url_for('admin.dashboard')
            if 'pago' in dest or 'deuda' in dest: target_url = url_for('admin.deudores_page')
            elif 'gasto' in dest: target_url = url_for('admin.expenses')
            elif 'usuario' in dest: target_url = url_for('admin.users')
            
            # Notificación tipo "Guía"
            notif_service.create_notification(current_user.id, f" Llama: Te estoy llevando a {dest}.", link=target_url)
            return jsonify({'response': friendly, 'status': 'info', 'redirect': target_url})

        # Default fallback
        return jsonify({'response': friendly, 'status': 'info'})

    except Exception as e:
        return jsonify({'response': f"Ups: {str(e)}", 'status': 'error'})

@admin_bp.route('/reports/send-weekly-summary', methods=['POST'])
@login_required
def send_weekly_summary_manual():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    try:
        from app.tasks import check_upcoming_payments
        # Use underlying app object
        app = current_app._get_current_object()
        
        # Run synchronous and FORCE send even if no alerts
        check_upcoming_payments(app, force=True)
        
        return jsonify({'success': True, 'message': 'Reporte semanal enviado al admin.'})
    except Exception as e:
        current_app.logger.error(f"Manual report error: {e}")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/reports/export-payments')
@login_required
def export_payments_csv():
    if current_user.role not in ('admin', 'supervisor'):
        return redirect(url_for('main.dashboard'))
    
    import csv
    from io import StringIO
    from flask import make_response
    
    # Get all payments or filtered by month? Ticket implies monthly but let's dump all for now or current month
    # "Listado de pagos del mes"
    today = datetime.utcnow().date()
    start_date = today.replace(day=1) # Start of this month
    
    payments = Payment.query.filter(Payment.date >= start_date).order_by(Payment.date.desc()).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Paciente', 'Monto', 'Descuento', 'Metodo', 'Referencia', 'Fecha', 'Notas'])
    
    for p in payments:
        patient_name = p.patient.username if p.patient else 'Unknown'
        cw.writerow([
            p.id, 
            patient_name, 
            p.amount, 
            p.discount, 
            p.method, 
            p.reference, 
            p.date.strftime('%Y-%m-%d %H:%M'),
            p.notes
        ])
        
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=pagos_{today.strftime('%Y_%m')}.csv"
    output.headers["Content-type"] = "text/csv"
    return output


@admin_bp.route('/sedes')
@login_required
def sedes_page():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/sedes_cards.html', active_page='admin_sedes')


@admin_bp.route('/deudores')
@login_required
def deudores_page():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/deudores.html', active_page='admin_deudores')


@admin_bp.route('/expenses')
@login_required
def expenses():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    financials = finance_service.get_therapist_financials()
    recent = finance_service.get_expenses() 
    
    return render_template('admin/expenses.html', 
                            therapist_financials=financials,
                            recent_expenses=recent,
                            current_date=datetime.now().strftime('%Y-%m-%d'),
                            active_page='admin_expenses')

@admin_bp.route('/expenses/create', methods=['POST'])
@login_required
def create_expense_route():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    data = request.form.to_dict()
    # Normalize therapist_id - if empty string, remove it so it's None or handle in service
    if not data.get('therapist_id'):
        data['therapist_id'] = None
    elif data.get('therapist_id') == '':
         data['therapist_id'] = None

    # Handle File Upload for Receipt
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            file.save(os.path.join(upload_dir, unique_name))
            data['receipt_image_path'] = f"receipts/{unique_name}"

    success, res = finance_service.create_expense(data)
    
    if success:
        flash('Gasto registrado, todo ok.', 'success')
    else:
        flash(f'Error al registrar: {res}', 'error')
        
    return redirect(url_for('admin.expenses'))

# --- JSON API endpoints for Angular Admin ---

@admin_bp.route('/api/therapist-financials')
@login_required
def api_therapist_financials():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    financials = finance_service.get_therapist_financials(month=month, year=year)
    result = []
    for f in financials:
        t = f['therapist']
        result.append({
            'therapist': {'id': t.id, 'username': t.username, 'salary_base': t.salary_base, 'contract_hours': t.contract_hours},
            'rate': f['rate'],
            'contract_hours': f['contract_hours'],
            'worked_hours': f['worked_hours'],
            'projected_pay': f['projected_pay'],
            'paid': f['paid'],
            'balance': f['balance'],
        })
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/api/expenses')
@login_required
def api_expenses():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    category = request.args.get('category')
    expenses = finance_service.get_expenses(start_date=start_date, end_date=end_date, category=category)
    result = []
    for e in expenses:
        result.append({
            'id': e.id,
            'category': e.category,
            'amount': e.amount,
            'date': e.date.strftime('%Y-%m-%d') if e.date else None,
            'description': e.description,
            'method': e.method,
            'receipt_image_path': e.receipt_image_path,
            'therapist': {'id': e.therapist.id, 'username': e.therapist.username} if e.therapist else None,
            'created_at': e.created_at.strftime('%Y-%m-%d %H:%M') if e.created_at else None,
        })
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/api/expenses/create', methods=['POST'])
@login_required
def api_create_expense():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    data = request.form.to_dict() if request.form else request.get_json(silent=True) or {}
    if not data.get('therapist_id'):
        data['therapist_id'] = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            file.save(os.path.join(upload_dir, unique_name))
            data['receipt_image_path'] = f"receipts/{unique_name}"
    success, res = finance_service.create_expense(data)
    if success:
        return jsonify({'success': True, 'message': 'Gasto registrado, listo.', 'expense': {
            'id': res.id, 'category': res.category, 'amount': res.amount, 'date': res.date.strftime('%Y-%m-%d') if res.date else None
        }})
    return jsonify({'success': False, 'error': res}), 400

@admin_bp.route('/api/contact-messages')
@login_required
def api_contact_messages():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    from app.models import ContactMessage
    import json
    messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    result = []
    for m in messages:
        analysis = None
        if m.ai_analysis:
            try:
                analysis = json.loads(m.ai_analysis)
            except Exception:
                analysis = {'raw': m.ai_analysis[:200]}
        result.append({
            'id': m.id,
            'first_name': m.first_name,
            'last_name': m.last_name,
            'email': m.email,
            'phone': m.phone,
            'subject': m.subject,
            'message': m.message,
            'service_interest': m.service_interest,
            'urgency': m.urgency,
            'status': m.status,
            'ai_analysis': analysis,
            'created_at': m.created_at.strftime('%d/%m/%Y %H:%M') if m.created_at else None,
        })
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/api/financial-summary')
@login_required
def api_financial_summary():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    financials = payment_service.get_financial_summary()
    return jsonify({'success': True, 'data': financials})

@admin_bp.route('/api/audit-stats')
@login_required
def api_audit_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        from app.models import SessionAudit, Appointment, User
        from sqlalchemy import func as sqlfunc

        total_audits = SessionAudit.query.filter(SessionAudit.audit_score.isnot(None)).count()
        avg_score = db.session.query(sqlfunc.avg(SessionAudit.audit_score)).filter(
            SessionAudit.audit_score.isnot(None)
        ).scalar() or 0

        recent_audits = db.session.query(
            SessionAudit, Appointment, User
        ).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).join(
            User, Appointment.therapist_id == User.id
        ).filter(
            SessionAudit.audit_score.isnot(None)
        ).order_by(SessionAudit.audited_at.desc()).limit(20).all()

        audit_rows = []
        for audit, appt, therapist in recent_audits:
            patient = User.query.get(appt.patient_id)
            audit_rows.append({
                'id': audit.id,
                'therapist': therapist.username,
                'patient': patient.username if patient else 'N/A',
                'date': appt.start_time.strftime('%d/%m/%Y') if appt.start_time else 'N/A',
                'score': round(audit.audit_score, 1) if audit.audit_score else 0,
                'status': audit.audit_status
            })

        therapist_scores = db.session.query(
            User.username,
            sqlfunc.avg(SessionAudit.audit_score).label('avg_score'),
            sqlfunc.count(SessionAudit.id).label('count')
        ).join(
            Appointment, SessionAudit.appointment_id == Appointment.id
        ).join(
            User, Appointment.therapist_id == User.id
        ).filter(
            SessionAudit.audit_score.isnot(None)
        ).group_by(User.id).all()

        data = {
            'total': total_audits,
            'avg_score': round(avg_score, 1),
            'recent': audit_rows,
            'by_therapist': [{'name': t[0], 'avg_score': round(t[1], 1), 'count': t[2]} for t in therapist_scores]
        }
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        current_app.logger.error(f"Error loading audit stats: {e}")
        return jsonify({'success': False, 'data': {'total': 0, 'avg_score': 0, 'recent': [], 'by_therapist': []}})

@admin_bp.route('/api/therapist-efficiency')
@login_required
def api_therapist_efficiency():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    try:
        from app.models import Appointment, SessionMetrics
        therapist_id = request.args.get('therapist_id', type=int)
        query = db.session.query(
            User.id.label('therapist_id'),
            User.username,
            sqlfunc.count(Appointment.id).label('total'),
            sqlfunc.avg(SessionMetrics.accurracy).label('avg_accuracy'),
            sqlfunc.count(sqlfunc.nullif(Appointment.status, 'cancelled')).label('completed')
        ).join(User, Appointment.therapist_id == User.id
        ).outerjoin(SessionMetrics, SessionMetrics.session_id == Appointment.id
        ).filter(User.role == 'terapista')
        if therapist_id:
            query = query.filter(User.id == therapist_id)
        rows = query.group_by(User.id).all()
        total_sessions = max(sum(r.total for r in rows), 1) if rows else 1
        breakdown = []
        for r in rows:
            completion = (r.completed / r.total * 100) if r.total else 0
            accuracy = r.avg_accuracy or 0
            efficiency = round((completion * 0.4 + accuracy * 0.6), 1)
            breakdown.append({
                'therapist_id': r.therapist_id,
                'name': r.username,
                'total_sessions': r.total,
                'completed': r.completed,
                'avg_accuracy': round(accuracy, 1),
                'efficiency': efficiency
            })
        overall = round(sum(e['efficiency'] for e in breakdown) / len(breakdown), 1) if breakdown else 0
        return jsonify({'success': True, 'overall': overall, 'breakdown': breakdown})
    except Exception as e:
        current_app.logger.error(f"Error loading therapist efficiency: {e}")
        return jsonify({'success': False, 'overall': 0, 'breakdown': []})

@admin_bp.route('/api/payments/all')
@login_required
def api_all_payments():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    from app.models import Payment, User
    payments = Payment.query.order_by(Payment.date.desc()).limit(500).all()
    result = []
    for p in payments:
        patient = User.query.get(p.patient_id)
        result.append({
            'id': p.id,
            'patient_id': p.patient_id,
            'patient_name': patient.username if patient else '',
            'amount': p.amount or 0,
            'discount': p.discount or 0,
            'method': p.method or '',
            'reference': p.reference or '',
            'date': p.date.strftime('%Y-%m-%dT%H:%M:%S') if p.date else '',
            'status': p.status or 'completed',
            'receipt_image_path': p.receipt_image_path or '',
            'document_number': getattr(p, 'document_number', '') or '',
            'guardian_name': getattr(p, 'guardian_name', '') or '',
        })
    return jsonify({'success': True, 'payments': result})

@admin_bp.route('/api/report-therapist-stats')
@login_required
def api_report_therapist_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    from app.models import SessionMetrics, Appointment
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    result = []
    for t in therapists:
        sessions = Appointment.query.filter_by(therapist_id=t.id, status='completed').count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=t.id).scalar() or 0
        result.append({'id': t.id, 'name': t.username, 'email': t.email, 'sessions': sessions, 'avg_accuracy': round(acc, 1)})
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/api/report-patient-stats')
@login_required
def api_report_patient_stats():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    from app.models import SessionMetrics
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    result = []
    for p in patients:
        plays = SessionMetrics.query.filter_by(user_id=p.id).count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
        result.append({'id': p.id, 'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc, 1)})
    return jsonify({'success': True, 'data': result})

@admin_bp.route('/api/overview')
@login_required
def api_admin_overview():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    overview = dashboard_service.get_admin_overview()
    return jsonify({'success': True, 'data': overview})

# --- End JSON API endpoints ---

@admin_bp.route('/messages')
@login_required
def messages():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    
    # NEW: Fetch contact messages
    contact_messages = ContactMessage.query.order_by(ContactMessage.created_at.desc()).all()
    return render_template('admin/messages.html', therapists=therapists, patients=patients, active_page='admin_messages', contact_messages=contact_messages)


@admin_bp.route('/csp-reports')
@login_required
def csp_reports():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since') # ISO date or empty

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f"%{q_directive}%"))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f"%{q_blocked}%"))
    if q_since:
        try:
            from datetime import datetime
            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('admin/csp_reports.html', pagination=pagination, active_page='admin_reports')


@admin_bp.route('/admin/api/tokens', methods=['GET', 'POST'])
@login_required
def admin_api_tokens():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        rotate = request.form.get('rotate') == '1'
        if rotate:
            rows = AdminAPIToken.query.filter_by(is_active=True).all()
            for r in rows:
                r.deactivate()
        token = secrets.token_urlsafe(32)
        token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
        new = AdminAPIToken(token_hash=token_hash, is_active=True)
        db.session.add(new)
        db.session.commit()
        # show plaintext token once via flash (admins must copy it)
        flash(f'Nuevo token creado. Copia y guarda ahora: {token}', 'success')

    tokens = AdminAPIToken.query.order_by(AdminAPIToken.created_at.desc()).all()
    return render_template('admin/api_tokens.html', tokens=tokens, active_page='admin_reports')


@admin_bp.route('/api/tokens/list', methods=['GET'])
@login_required
def api_tokens_list_json():

    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    tokens = AdminAPIToken.query.order_by(AdminAPIToken.created_at.desc()).all()
    return jsonify({'tokens': [{'id': t.id, 'created_at': t.created_at.isoformat() if t.created_at else None, 'is_active': t.is_active} for t in tokens]})


@admin_bp.route('/api/tokens/create', methods=['POST'])
@login_required
def api_tokens_create_json():

    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    data = request.get_json(silent=True) or {}
    rotate = data.get('rotate', False)
    if rotate:
        rows = AdminAPIToken.query.filter_by(is_active=True).all()
        for r in rows:
            r.deactivate()
    token = secrets.token_urlsafe(32)
    token_hash = bcrypt.generate_password_hash(token).decode('utf-8')
    new = AdminAPIToken(token_hash=token_hash, is_active=True)
    db.session.add(new)
    db.session.commit()
    return jsonify({'token': token, 'id': new.id, 'created_at': new.created_at.isoformat() if new.created_at else None, 'is_active': True})


@admin_bp.route('/api/tokens/deactivate/<int:token_id>', methods=['POST'])
@login_required
def api_tokens_deactivate_json(token_id):

    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    t = AdminAPIToken.query.get_or_404(token_id)
    t.deactivate()
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/admin/api/tokens/deactivate/<int:token_id>', methods=['POST'])
@login_required
def deactivate_admin_token(token_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    t = AdminAPIToken.query.get_or_404(token_id)
    t.deactivate()
    db.session.commit()
    flash('Token desactivado, listo.', 'success')
    return redirect(url_for('admin.admin_api_tokens'))


@admin_bp.route('/admin/api/csp-reports')
def _admin_api_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Allow session-based admin users
        if current_user and getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'role', None) == 'admin':
            return f(*args, **kwargs)

        # Allow bearer token via ADMIN_API_TOKEN env var
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1].strip()
            expected = os.getenv('ADMIN_API_TOKEN')
            if expected and token == expected:
                return f(*args, **kwargs)

            # Otherwise check active hashed tokens in DB
            try:
                token_rows = AdminAPIToken.query.filter_by(is_active=True).all()
                for row in token_rows:
                    if bcrypt.check_password_hash(row.token_hash, token):
                        return f(*args, **kwargs)
            except Exception:
                pass

        return jsonify({'error': 'No autorizado'}), 403
    return wrapper


@admin_bp.route('/api/csp-reports')
@_admin_api_auth
def api_csp_reports():

    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 25))
    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since')

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f"%{q_directive}%"))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f"%{q_blocked}%"))
    if q_since:
        try:
            from datetime import datetime
            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = []
    for r in pagination.items:
        items.append({
            'id': r.id,
            'received_at': r.received_at.isoformat(),
            'document_uri': r.document_uri,
            'violated_directive': r.violated_directive,
            'blocked_uri': r.blocked_uri,
            'ip_address': r.ip_address,
            'user_id': r.user_id
        })

    return jsonify({
        'items': items,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'total': pagination.total,
        'pages': pagination.pages
    })


@admin_bp.route('/csp-reports/export')
@_admin_api_auth
def export_csp_reports():
    # For non-UI API token auth, we cannot redirect; return 403 instead
    if not (current_user and getattr(current_user, 'is_authenticated', False) and getattr(current_user, 'role', None) == 'admin'):
        # If token auth used, allow continuing; _admin_api_auth already allowed or rejected.
        # For UI access, ensure we don't redirect to main when using token auth — token users should download CSV.
        # Continue and let _admin_api_auth have validated the request.
        pass

    q_directive = request.args.get('directive')
    q_blocked = request.args.get('blocked_uri')
    q_since = request.args.get('since')

    query = CSPReport.query.order_by(CSPReport.received_at.desc())
    if q_directive:
        query = query.filter(CSPReport.violated_directive.ilike(f"%{q_directive}%"))
    if q_blocked:
        query = query.filter(CSPReport.blocked_uri.ilike(f"%{q_blocked}%"))
    if q_since:
        try:
            from datetime import datetime
            since_dt = datetime.fromisoformat(q_since)
            query = query.filter(CSPReport.received_at >= since_dt)
        except Exception:
            pass

    reports = query.all()

    # Build CSV
    import csv
    from io import StringIO
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['id','received_at','document_uri','violated_directive','blocked_uri','ip_address','user_id'])
    for r in reports:
        cw.writerow([r.id, r.received_at.isoformat(), r.document_uri or '', r.violated_directive or '', r.blocked_uri or '', r.ip_address or '', r.user_id or ''])

    output = si.getvalue()
    from flask import make_response
    resp = make_response(output)
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = 'attachment; filename=csp_reports.csv'
    return resp

@admin_bp.route('/profile')
@login_required
def profile():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/profile.html', active_page='admin_dashboard')

@admin_bp.route('/payments')
@login_required
def payments():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Auto-check overdue stats on load
    deactivated = payment_service.check_and_deactivate_overdue()
    if deactivated > 0:
        flash(f'{deactivated} usuarios desactivados por falta de pago.', 'warning')

    patients_status = payment_service.get_patients_payment_status()
    therapists = User.query.filter_by(role='terapista').all()
    sedes = Sede.query.all()
    payment_history = payment_service.get_payment_history()
    return render_template('admin/payments.html', patients=patients_status, therapists=therapists, sedes=sedes, payment_history=payment_history, active_page='admin_payments')

@admin_bp.route('/api/payment-info/<int:patient_id>')
@login_required
def get_payment_info(patient_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'No autorizado'}), 403
    
    info = payment_service.get_billing_info(patient_id)
    if not info:
        return jsonify({'error': 'Usuario no encontrado'}), 404
        
    return jsonify(info)

@admin_bp.route('/payments/register', methods=['POST'])
@login_required
def register_payment():
    if current_user.role not in ('admin', 'supervisor'):
        return redirect(url_for('main.dashboard'))
    # Collect form data and validate
    discount_input = request.form.get('discount')
    if not discount_input or discount_input.strip() == '':
        discount_input = 0.0

    next_date_input = request.form.get('next_due_date')
    if not next_date_input or next_date_input.strip() == '':
         next_date_input = None
         
    form = {
        'patient_id': request.form.get('patient_id'),
        'amount': request.form.get('amount'),
        'discount': discount_input,
        'method': request.form.get('method'),
        'reference': request.form.get('reference'),
        'next_due_date': next_date_input
    }

    # Manual payment date extraction
    payment_date_str = request.form.get('payment_date')
    payment_date_obj = None
    if payment_date_str:
        try:
             payment_date_obj = datetime.strptime(payment_date_str, '%Y-%m-%d')
        except ValueError:
             pass 

    data, errors = validate_payment_register(form)
    if errors:
        flash('Errores en el formulario de pago: ' + json.dumps(errors), 'error')
        current_app.logger.debug(f"Payment register validation errors: {errors}")
        return redirect(url_for('admin.payments'))

    patient_id = data['patient_id']
    amount = data['amount']
    discount = data.get('discount', 0.0)
    method = data['method']
    reference = data.get('reference')
    next_due_date = data.get('next_due_date')
    
    # Handle File Upload
    receipt_path = None
    if 'receipt' in request.files:
        file = request.files['receipt']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            unique_name = f"{uuid.uuid4().hex}{ext}"
            
            upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'receipts')
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
                
            file.save(os.path.join(upload_dir, unique_name))
            
            # Store relative path for template usage
            # Fix: Previously it was storing "uploads/receipts/...", but base UPLOAD_FOLDER is already instance/uploads
            # So the relative path from UPLOAD_FOLDER should be just "receipts/..."
            receipt_path = f"receipts/{unique_name}"

    try:
         discount_val = float(discount) if discount else 0.0
    except:
         discount_val = 0.0


    document_number = request.form.get('document_number')
    guardian_name = request.form.get('guardian_name')
    
    if document_number or guardian_name:
        patient = User.query.get(patient_id)
        if patient:
            if document_number: patient.document_number = document_number
            if guardian_name: patient.guardian_name = guardian_name
            db.session.commit()

    success, result_or_payment = payment_service.register_payment(patient_id, float(amount), method, reference, next_due_date, receipt_path, discount_val, payment_date=payment_date_obj)
    
    msg_text = "Pago registrado, todo ok" if success else str(result_or_payment)
    
    # Check if this is an AJAX request (from deudores.html)
    is_ajax = False
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        is_ajax = True
    elif hasattr(request.accept_mimetypes, 'accept_json') and request.accept_mimetypes.accept_json:
        is_ajax = True
    elif 'application/json' in request.headers.get('Accept', ''):
        is_ajax = True

    if is_ajax:
        # Return JSON for AJAX clients
        if success:
            receipt_url = url_for('admin.download_receipt', payment_id=result_or_payment.id)
            return jsonify({'success': True, 'message': msg_text, 'receipt_url': receipt_url}), 200
        else:
            return jsonify({'success': False, 'error': msg_text}), 400
    
    # For traditional form submissions, use flash messages
    if success:
        flash(msg_text, 'success')
    else:
        flash(msg_text, 'error')
    
    return redirect(url_for('admin.payments'))

@admin_bp.route('/payments/history/<int:patient_id>')
@login_required
def payment_history(patient_id):
    if current_user.role not in ('admin', 'supervisor'):
        return redirect(url_for('main.dashboard'))
    
    patient = User.query.get_or_404(patient_id)
    payments = Payment.query.filter_by(patient_id=patient_id).order_by(Payment.date.desc()).all()
    
    return render_template('admin/payment_history.html', patient=patient, payments=payments, active_page='admin_payments')

@admin_bp.route('/payments/settings', methods=['POST'])
@login_required
def update_payment_settings():
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
        
    patient_id = request.form.get('patient_id')
    amount = request.form.get('payment_amount')
    due_date = request.form.get('payment_due_date')
    frequency = request.form.get('payment_plan')
    
    success, msg = payment_service.update_payment_settings(patient_id, amount, due_date, frequency)
    if success:
        flash(msg, 'success')
    else:
        flash(msg, 'error')
    
    return redirect(url_for('admin.payments'))

@admin_bp.route('/payments/delete/<int:payment_id>', methods=['POST'])
@login_required
def delete_payment(payment_id):
    if current_user.role != 'admin':
        return redirect(url_for('main.dashboard'))
    
    try:
        payment = Payment.query.get_or_404(payment_id)
        
        if payment.receipt_image_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], payment.receipt_image_path)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        db.session.delete(payment)
        db.session.commit()
        flash('Pago eliminado.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el pago: {str(e)}', 'error')
        
    return redirect(request.referrer or url_for('admin.payments'))

@admin_bp.route('/analyze-receipt', methods=['POST'])
@login_required
def analyze_receipt():
    """Analizar voucher de pago con IA"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    if 'receipt' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['receipt']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    patient_id = request.form.get('patient_id', type=int)

    try:
        import json
        from app.services.llm_automation_service import analyze_receipt_image
        import tempfile
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            print(f"DEBUG: Analyzing receipt: {tmp_path}")
            data = analyze_receipt_image(tmp_path)

            if 'transaction_id' in data and 'reference' not in data:
                data['reference'] = data['transaction_id']
            if 'sender_name' in data and 'method' not in data:
                data['method'] = 'yape/plin'

            if patient_id:
                try:
                    from app.services.payment_service import PaymentService
                    billing = PaymentService().get_billing_info(patient_id)
                    if billing and billing.get('suggested_date'):
                        data['next_due_date'] = billing['suggested_date']
                except Exception as billing_err:
                    print(f"WARN: Could not calculate next_due_date: {billing_err}")

            os.unlink(tmp_path)
            return jsonify(data)

        except Exception as llm_err:
            print(f"ERROR with Ollama OCR: {llm_err}")
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            data = {
                'amount': None, 
                'date': datetime.now().strftime('%Y-%m-%d'), 
                'reference': None, 
                'method': 'transferencia',
                'warning': 'Error al analizar el voucher. Ingresa los datos manualmente.'
            }
            if patient_id:
                try:
                    from app.services.payment_service import PaymentService
                    billing = PaymentService().get_billing_info(patient_id)
                    if billing and billing.get('suggested_date'):
                        data['next_due_date'] = billing['suggested_date']
                except Exception:
                    pass
            return jsonify(data)
        
    except Exception as e:
        print(f"ERROR in analyze_receipt: {str(e)}")
        return jsonify({'error': str(e)}), 200

@admin_bp.route('/sessions')
@login_required
def sessions_calendar():
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    
    return render_template('admin/sessions.html', 
                           therapists=therapists, 
                           patients=patients, 
                           active_page='admin_sessions')

@admin_bp.route('/api/sessions')
@login_required
def get_sessions_api():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        start_str = request.args.get('start') 
        end_str = request.args.get('end')
        therapist_id = request.args.get('therapist_id')
        
        query = Appointment.query
        
        if start_str and len(start_str) > 5:
            try:
                # Handle ISO format including Z or offset
                simple_start = start_str.split('T')[0]
                start_dt = datetime.strptime(simple_start, '%Y-%m-%d')
                query = query.filter(Appointment.start_time >= start_dt)
            except Exception:
                pass # Fallback to no filter

        if end_str and len(end_str) > 5:
            try:
                simple_end = end_str.split('T')[0]
                end_dt = datetime.strptime(simple_end, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(Appointment.start_time <= end_dt)
            except Exception:
                pass

        if therapist_id and therapist_id != 'all' and therapist_id != 'undefined':
            try:
                tid = int(therapist_id)
                query = query.filter(Appointment.therapist_id == tid)
            except ValueError:
                pass
            
        appointments = query.all()
        
        events = []
        for app in appointments:
            try:
                color = '#3788d8'
                if app.status == 'completed': color = '#10b981'
                elif app.status == 'cancelled': color = '#ef4444'
                elif app.status == 'scheduled': color = '#3b82f6'
                
                p_name = '???'
                # Use getattr to prevent crash if relationship is broken
                if getattr(app, 'patient', None):
                    p_name = app.patient.username
                
                t_name = '???'
                if getattr(app, 'therapist', None):
                    t_name = app.therapist.username
                
                # Check times
                if not app.start_time:
                    continue

                evt = {
                    'id': app.id,
                    'title': app.title if app.title else f"{p_name} ({t_name})",
                    'start': app.start_time.isoformat(),
                    'end': app.end_time.isoformat() if app.end_time else None,
                    'backgroundColor': color,
                    'borderColor': color,
                    'extendedProps': {
                        'therapist_id': app.therapist_id,
                        'patient_id': app.patient_id,
                        'therapist': t_name,
                        'patient': p_name,
                        'status': app.status,
                        'notes': app.notes
                    }
                }
                events.append(evt)
            except Exception as e_inner:
                current_app.logger.error(f"Error packing event {app.id}: {e_inner}")
                continue
            
        return jsonify(events)
    except Exception as e:
        current_app.logger.error(f"API Sessions Error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/sessions/batch', methods=['POST'])
@login_required
@csrf.exempt
def batch_create_sessions():
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
        
    data = request.json
    therapist_id = data.get('therapist_id')
    patient_id = data.get('patient_id')
    start_time_str = data.get('start_time') # HH:MM
    end_time_str = data.get('end_time') # HH:MM
    title_prefix = data.get('title_prefix', '')
    title = data.get('title', '')
    sede = data.get('sede', '')
    
    if not all([therapist_id, patient_id, start_time_str, end_time_str]):
        return jsonify({'error': 'Faltan datos requeridos'}), 400
        
    try:
        start_h, start_m = map(int, start_time_str.split(':'))
        end_h, end_m = map(int, end_time_str.split(':'))
        
        created_count = 0
        created_ids = []
        
        specific_dates = data.get('dates')  # list of YYYY-MM-DD
        
        if specific_dates:
            if len(specific_dates) > 5:
                return jsonify({'error': 'Máximo 5 fechas'}), 400
            for date_str in specific_dates:
                current_date = datetime.strptime(date_str, '%Y-%m-%d')
                session_start = current_date.replace(hour=start_h, minute=start_m)
                session_end = current_date.replace(hour=end_h, minute=end_m)
                if session_end < session_start:
                    session_end += timedelta(days=1)
                session_title = title if title else (f"{title_prefix} - {date_str}" if title_prefix else f"Sesión {date_str}")
                appt = Appointment(
                    therapist_id=therapist_id,
                    patient_id=patient_id,
                    title=session_title,
                    start_time=session_start,
                    end_time=session_end,
                    status='scheduled',
                    location=sede,
                    created_at=datetime.utcnow()
                )
                db.session.add(appt)
                db.session.flush()
                created_ids.append(appt.id)
                created_count += 1
            db.session.commit()
            return jsonify({
                'success': True,
            'message': f'Se crearon {created_count} sesiones, todo ok.',
                'session_ids': created_ids
            })
        
        # Legacy mode: week-based recurrence
        start_date_str = data.get('start_date')
        days_of_week = data.get('days')
        cycle_weeks = int(data.get('weeks', 4))
        
        if not all([start_date_str, days_of_week]):
            return jsonify({'error': 'Faltan datos requeridos'}), 400
            
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date_iter = start_date + timedelta(weeks=cycle_weeks)
        
        total_sessions = 0
        temp_date = start_date
        while temp_date < end_date_iter:
            if temp_date.weekday() in days_of_week:
                total_sessions += 1
            temp_date += timedelta(days=1)
            
        session_counter = 1
        current_date_iter = start_date
        
        while current_date_iter < end_date_iter:
            if current_date_iter.weekday() in days_of_week:
                session_start = current_date_iter.replace(hour=start_h, minute=start_m)
                session_end = current_date_iter.replace(hour=end_h, minute=end_m)
                if session_end < session_start:
                    session_end += timedelta(days=1)
                if title_prefix and title_prefix.strip():
                     title_text = f"{title_prefix} ({session_counter}/{total_sessions})"
                else:
                     title_text = f"Sesión {session_counter}/{total_sessions}"
                appt = Appointment(
                    therapist_id=therapist_id,
                    patient_id=patient_id,
                    title=title_text,
                    start_time=session_start,
                    end_time=session_end,
                    status='scheduled',
                    created_at=datetime.utcnow()
                )
                db.session.add(appt)
                db.session.flush()
                created_ids.append(appt.id)
                created_count += 1
                session_counter += 1
            current_date_iter += timedelta(days=1)
            
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Se crearon {created_count} sesiones, listo.',
            'session_ids': created_ids
        })
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/sessions/<int:session_id>', methods=['PUT'])
@login_required
def update_session(session_id):
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    appt = Appointment.query.get(session_id)
    if not appt:
        return jsonify({'error': 'Session not found'}), 404
        
    try:
        if 'title' in data:
            appt.title = data['title']
        
        # Parse ISO string → datetime object (naive Peru local)
        if 'start_time' in data and isinstance(data['start_time'], str) and 'T' in data['start_time']:
            appt.start_time = datetime.fromisoformat(data['start_time'])
        elif 'start_date' in data and 'start_time' in data:
            start_dt = datetime.strptime(f"{data['start_date']} {data['start_time']}", "%Y-%m-%d %H:%M")
            appt.start_time = start_dt
        
        if 'end_time' in data and isinstance(data['end_time'], str) and 'T' in data['end_time']:
            end_dt = datetime.fromisoformat(data['end_time'])
            if appt.start_time and end_dt < appt.start_time:
                end_dt += timedelta(days=1)
            appt.end_time = end_dt
        elif 'end_time' in data and data.get('start_date'):
            end_dt = datetime.strptime(f"{data['start_date']} {data['end_time']}", "%Y-%m-%d %H:%M")
            if end_dt < appt.start_time:
                end_dt += timedelta(days=1)
            appt.end_time = end_dt
            
        if 'notes' in data:
            appt.notes = data['notes']
            
        if 'status' in data:
            appt.status = data['status']
            
        db.session.commit()
        return jsonify({'success': True, 'message': 'Sesión actualizada'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/api/daily-reports', methods=['GET'])
@login_required
def api_daily_reports():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    start = request.args.get('start')
    end = request.args.get('end')
    
    if not start or not end:
        return jsonify({'success': False, 'error': 'start y end son requeridos (YYYY-MM-DD)'}), 400

    try:
        from app.services.report_service import ReportService
        rs = ReportService()
        reports = rs.get_daily_reports(start, end)
        return jsonify({'success': True, 'reports': reports})
    except Exception as e:
        current_app.logger.error(f"Error fetching daily reports: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/weekly-summary', methods=['GET'])
@login_required
def api_weekly_summary():

    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    week_start = request.args.get('week_start')
    if not week_start:
        # Default to current week (Monday)
        today = datetime.utcnow().date()
        week_start = (today - timedelta(days=today.weekday())).isoformat()

    try:
        from app.services.report_service import ReportService
        rs = ReportService()
        summary = rs.get_weekly_summary(week_start)
        return jsonify({'success': True, 'summary': summary})
    except Exception as e:
        current_app.logger.error(f"Error fetching weekly summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/api/reports/accumulate', methods=['POST'])
@login_required
def api_accumulate_reports():
    """Acumular reportes diarios"""
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    report_date = request.args.get('date')
    
    from app.services.report_service import ReportService
    rs = ReportService()

    # Get all therapists with completed sessions today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if report_date:
        try:
            today_start = datetime.strptime(report_date, '%Y-%m-%d')
        except:
            pass
    
    tomorrow = today_start + timedelta(days=1)

    therapists = User.query.filter_by(role='terapista', is_active=True).all()
    accumulated = 0

    for therapist in therapists:
        patients = therapist.associated_patients.filter_by(role='jugador').all()
        for patient in patients:
            has_sessions = Appointment.query.filter(
                Appointment.patient_id == patient.id,
                Appointment.therapist_id == therapist.id,
                Appointment.start_time >= today_start,
                Appointment.start_time < tomorrow,
                Appointment.status == 'completed'
            ).count()
            
            if has_sessions > 0:
                rs.generate_daily_report(patient.id, therapist.id, today_start.strftime('%Y-%m-%d'))
                accumulated += 1

    return jsonify({
        'success': True,
        'message': f'Reportes acumulados para {accumulated} pacientes',
        'date': today_start.strftime('%Y-%m-%d')
    })


@admin_bp.route('/api/reports/monthly', methods=['GET'])
@login_required
def api_monthly_reports():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)

    from app.services.report_service import ReportService
    rs = ReportService()
    summary = rs.get_monthly_summary(year, month)
    return jsonify({'success': True, 'summary': summary})


@admin_bp.route('/api/reports/quarterly', methods=['GET'])
@login_required
def api_quarterly_reports():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    quarter = request.args.get('quarter', type=int, default=(datetime.utcnow().month - 1) // 3 + 1)

    from app.services.report_service import ReportService
    rs = ReportService()
    summary = rs.get_quarterly_summary(year, quarter)
    return jsonify({'success': True, 'summary': summary})


@admin_bp.route('/api/reports/generate-all-weekly', methods=['POST'])
@login_required
def api_generate_all_weekly():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    week_start = request.args.get('week_start')
    from app.services.report_service import ReportService
    rs = ReportService()
    generated = rs.generate_all_weekly_reports(week_start)

    from app.models import Notification
    admin_users = User.query.filter_by(role='admin').all()
    for admin in admin_users:
        notif = Notification(
            user_id=admin.id,
            title='Reportes Semanales Generados',
            message=f'Se generaron {len(generated)} reportes semanales automaticamente.',
            type='reportes'
        )
        db.session.add(notif)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{len(generated)} reportes semanales generados',
        'count': len(generated)
    })


@admin_bp.route('/api/reports/generate-monthly', methods=['POST'])
@login_required
def api_generate_monthly():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)

    from app.services.report_service import ReportService
    rs = ReportService()
    generated = rs.generate_all_monthly_reports(year, month)

    return jsonify({
        'success': True,
        'message': f'{len(generated)} reportes mensuales generados',
        'count': len(generated)
    })


@admin_bp.route('/api/reports/generate-quarterly', methods=['POST'])
@login_required
def api_generate_quarterly():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    quarter = request.args.get('quarter', type=int, default=(datetime.utcnow().month - 1) // 3 + 1)

    from app.services.report_service import ReportService
    rs = ReportService()
    generated = rs.generate_all_quarterly_reports(year, quarter)

    return jsonify({
        'success': True,
        'message': f'{len(generated)} reportes trimestrales generados',
        'count': len(generated)
    })


@admin_bp.route('/api/reports/patient-monthly/<int:patient_id>', methods=['GET'])
@login_required
def api_patient_monthly_reports(patient_id):
    if current_user.role not in ('admin', 'terapista', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    reports = MonthlyReport.query.filter_by(patient_id=patient_id).order_by(MonthlyReport.year.desc(), MonthlyReport.month.desc()).all()
    return jsonify({'success': True, 'reports': [{
        'id': r.id, 'month': r.month, 'year': r.year,
        'sessions_count': r.sessions_count, 'avg_score': r.avg_score,
        'objectives_achieved': r.objectives_achieved, 'objectives_total': r.objectives_total,
        'report_text': r.report_text, 'created_at': r.created_at.isoformat(),
    } for r in reports]})


@admin_bp.route('/api/reports/patient-quarterly/<int:patient_id>', methods=['GET'])
@login_required
def api_patient_quarterly_reports(patient_id):
    if current_user.role not in ('admin', 'terapista', 'supervisor'):
        return jsonify({'error': 'Unauthorized'}), 403

    reports = QuarterlyReport.query.filter_by(patient_id=patient_id).order_by(QuarterlyReport.year.desc(), QuarterlyReport.quarter.desc()).all()
    return jsonify({'success': True, 'reports': [{
        'id': r.id, 'quarter': r.quarter, 'year': r.year,
        'sessions_count': r.sessions_count, 'avg_score': r.avg_score,
        'objectives_achieved': r.objectives_achieved, 'objectives_total': r.objectives_total,
        'report_text': r.report_text, 'created_at': r.created_at.isoformat(),
    } for r in reports]})


def download_receipt(payment_id):
    from flask import flash, redirect, url_for
    from flask_login import current_user
    
    if current_user.role not in ('admin', 'supervisor'):
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))

    payment = Payment.query.get_or_404(payment_id)
    patient = User.query.get(payment.patient_id)
    
    if not patient:
        flash("Paciente no encontrado para este pago.", "error")
        return redirect(url_for('admin.users'))

    if request.method == 'POST':
        # Retrieve fields to rectify
        doc_number = request.form.get('document_number')
        g_name = request.form.get('guardian_name')
        concept = request.form.get('concept')
        
        # Save rectified data for the future
        if doc_number: patient.document_number = doc_number
        if g_name: patient.guardian_name = g_name
        if concept: payment.notes = concept
        
        db.session.commit()

    pdf_buffer = generate_receipt_pdf(payment, patient)
    
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"Recibo_JP2_REC-{payment.id:06d}.pdf",
        mimetype='application/pdf'
    )

@admin_bp.route('/api/logs', methods=['GET'])
@login_required
def admin_api_logs():
    if current_user.role not in ('admin', 'supervisor'):
        return jsonify({'success': False, 'error': 'Acceso denegado'}), 403
    from app.services.log_service import log_capture_handler
    level = request.args.get('level')
    limit = request.args.get('limit', 100, type=int)
    search = request.args.get('search')
    logs = log_capture_handler.get_logs(level=level, limit=limit, search=search)
    return jsonify({'success': True, 'logs': logs})