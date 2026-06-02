from flask import Blueprint, request, jsonify, current_app, url_for
from flask_login import login_required, current_user
from app.models import db, User, Notification, Appointment, Message, Game, SessionMetrics, SessionImage, ContactMessage, Sede, Payment
from app.services.appointment_service import AppointmentService
from app.services.game_service import GameService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.patient_service import PatientService
from app.services.dashboard_service import DashboardService
from app.services.report_service import ReportService
import json, os, time, warnings
warnings.filterwarnings('ignore', message='.*google.generativeai.*ended.*')
try:
    import google.generativeai as genai
except ImportError:
    genai = None
try:
    from groq import Groq
except ImportError:
    Groq = None
try:
    import ollama
    _ollama_client = ollama.Client(host='http://127.0.0.1:11434')
    _ollama_client.list()
except Exception:
    _ollama_client = None
from app.services.google_drive_service import GoogleDriveService
from app.services.ai_service import predict_level, start_async_training
from app.utils import get_user_today_utc_range, get_user_now, localize_datetime_for_display, get_user_timezone
from app.schemas import AssignTherapistSchema, UpdateUserSchema, SendMessageSchema
from app.extensions import bcrypt, limiter, csrf
from app.services.email_service import EmailService
from app.services.financial_service import FinancialService
from app.utils.api_helpers import api_response
from app.services.availability_service import AvailabilityService
from datetime import datetime, timedelta, timezone
import json
import os
import uuid
from werkzeug.utils import secure_filename
import requests
from sqlalchemy import or_, func


from app.routes.api import api_bp
@api_bp.route('/notifications')
@login_required
def get_notifications():
    notifications = notification_service.get_unread_notifications(current_user.id)
    result = [{
        'id': n.id,
        'title': n.title,
        'type': n.type or 'info',
        'message': n.message,
        'timestamp': n.timestamp.strftime('%d %b, %H:%M'),
        'link': n.link
    } for n in notifications]
    return jsonify(result)

@api_bp.route('/notifications/mark-read', methods=['POST'])
@login_required
@csrf.exempt
def mark_notifications_read():
    try:
        data = request.get_json() or {}
        notif_id = data.get('id')
        if notif_id:
            notification_service.mark_one_read(current_user.id, notif_id)
        else:
            notification_service.mark_all_as_read(current_user.id)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@api_bp.route('/notifications/create', methods=['POST'])
@login_required
@csrf.exempt
def create_notification():
    try:
        data = request.get_json()
        message = data.get('message')
        title = data.get('title')
        notif_type = data.get('type', 'info')
        link = data.get('link')

        if not message:
            return jsonify({'success': False, 'message': 'Mensaje es requerido'}), 400

        notification_service.create_notification(
            user_id=current_user.id,
            title=title,
            message=message,
            notif_type=notif_type,
            link=link
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

