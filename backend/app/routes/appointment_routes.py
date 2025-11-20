from flask import Blueprint, request, jsonify
from ..models.appointments import Appointment
from ..extensions import db
from datetime import datetime

appointment_bp = Blueprint('appointments', __name__)


@appointment_bp.route('/', methods=['GET'])
def list_appointments():
    appts = Appointment.query.order_by(Appointment.start_time.desc()).all()
    return jsonify([a.to_dict() for a in appts])


@appointment_bp.route('/', methods=['POST'])
def create_appointment():
    data = request.get_json() or {}
    start = data.get('start_time')
    end = data.get('end_time')
    appt = Appointment(
        patient_id=data.get('patient_id'),
        therapy_id=data.get('therapy_id'),
        therapist_id=data.get('therapist_id'),
        start_time=datetime.fromisoformat(start) if start else datetime.utcnow(),
        end_time=datetime.fromisoformat(end) if end else None,
        status=data.get('status', 'scheduled')
    )
    db.session.add(appt)
    db.session.commit()
    return jsonify(appt.to_dict()), 201
