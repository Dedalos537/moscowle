from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app.models import User, Appointment, SessionMetrics, db
from app.services.dashboard_service import DashboardService
from sqlalchemy import func
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
dashboard_service = DashboardService()

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    
    overview = dashboard_service.get_admin_overview()
    return render_template('admin/dashboard.html', overview=overview, active_page='admin_dashboard')

@admin_bp.route('/users')
@login_required
def users():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    users = User.query.order_by(User.created_at.desc()).all()
    therapists = User.query.filter_by(role='terapista').order_by(User.username.asc()).all()
    return render_template('admin/users.html', users=users, therapists=therapists, active_page='admin_users')

@admin_bp.route('/games')
@login_required
def games():
    if current_user.role != 'admin':
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
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    # Aggregate simple stats per therapist and patient
    therapists = User.query.filter_by(role='terapista').all()
    t_rows = []
    for t in therapists:
        count_appts = Appointment.query.filter_by(therapist_id=t.id).count()
        avg_acc = db.session.query(func.avg(SessionMetrics.accurracy)).scalar() or 0
        t_rows.append({'name': t.username, 'email': t.email, 'sessions': count_appts, 'avg_accuracy': round(avg_acc,1)})
    patients = User.query.filter_by(role='jugador').all()
    p_rows = []
    for p in patients:
        plays = SessionMetrics.query.filter_by(user_id=p.id).count()
        acc = db.session.query(func.avg(SessionMetrics.accurracy)).filter_by(user_id=p.id).scalar() or 0
        p_rows.append({'name': p.username, 'email': p.email, 'plays': plays, 'avg_accuracy': round(acc,1)})
    return render_template('admin/reports.html', therapists=t_rows, patients=p_rows, active_page='admin_reports')

@admin_bp.route('/messages')
@login_required
def messages():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    therapists = User.query.filter_by(role='terapista', is_active=True).order_by(User.username.asc()).all()
    patients = User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
    return render_template('admin/messages.html', therapists=therapists, patients=patients, active_page='admin_messages')

@admin_bp.route('/profile')
@login_required
def profile():
    if current_user.role != 'admin':
        flash('Acceso denegado.', 'error')
        return redirect(url_for('main.dashboard'))
    return render_template('admin/profile.html', active_page='admin_dashboard')
