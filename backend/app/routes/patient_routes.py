from flask import Blueprint, request, jsonify
from ..models.patient import Patient
from ..extensions import db

patient_bp = Blueprint('patients', __name__)


@patient_bp.route('/', methods=['GET'])
def list_patients():
    patients = Patient.query.all()
    return jsonify([p.to_dict() for p in patients])


@patient_bp.route('/', methods=['POST'])
def create_patient():
    data = request.get_json() or {}
    p = Patient(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        medical_record=data.get('medical_record')
    )
    db.session.add(p)
    db.session.commit()
    return jsonify(p.to_dict()), 201
