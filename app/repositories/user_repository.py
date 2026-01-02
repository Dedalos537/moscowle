from app.models import User
from app.extensions import db

class UserRepository:
    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_by_id(user_id):
        return User.query.get(int(user_id))

    @staticmethod
    def count_by_role(role):
        return User.query.filter_by(role=role).count()

    @staticmethod
    def get_active_patients_by_therapist(therapist_id):
        return User.query.filter_by(role='jugador', is_active=True, assigned_therapist_id=therapist_id).all()

    @staticmethod
    def count_active_patients_by_therapist(therapist_id):
        return User.query.filter_by(role='jugador', is_active=True, assigned_therapist_id=therapist_id).count()

    @staticmethod
    def save(user):
        db.session.add(user)
        db.session.commit()
        return user
