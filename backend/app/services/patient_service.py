from ..models.patient import Patient
from ..extensions import db


def get_all_patients():
    return Patient.query.all()


def create_patient(data: dict):
    p = Patient(
        first_name=data.get('first_name'),
        last_name=data.get('last_name'),
        dob=data.get('dob'),
        medical_record=data.get('medical_record')
    )
    db.session.add(p)
    db.session.commit()
    return p
