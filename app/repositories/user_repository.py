from app.extensions import db
from app.models import User


class UserRepository:
    @staticmethod
    def get_by_email(email):
        return User.query.filter_by(email=email).first()

    @staticmethod
    def get_by_login_code(code):
        if not code:
            return None
        return User.query.filter_by(login_code=code.upper().strip()).first()

    @staticmethod
    def get_by_id(user_id):
        return User.query.get(int(user_id))

    @staticmethod
    def count_by_role(role):
        return User.query.filter_by(role=role).count()

    @staticmethod
    def get_active_patients_by_therapist(therapist_id):
        therapist = User.query.get(therapist_id)
        if not therapist:
            return []

        m2m = therapist.associated_patients.filter_by(role='jugador', is_active=True).all()
        legacy = [p for p in therapist.assigned_patients if p.role == 'jugador' and p.is_active]

        merged = {p.id: p for p in m2m}
        for p in legacy:
            merged[p.id] = p

        return list(merged.values())

    @staticmethod
    def get_all_patients_by_therapist(therapist_id):
        therapist = User.query.get(therapist_id)
        if not therapist:
            return []

        m2m = therapist.associated_patients.filter_by(role='jugador').all()
        legacy = [p for p in therapist.assigned_patients if p.role == 'jugador']

        merged = {p.id: p for p in m2m}
        for p in legacy:
            merged[p.id] = p

        return list(merged.values())

    @staticmethod
    def count_active_patients_by_therapist(therapist_id):
        therapist = User.query.get(therapist_id)
        if not therapist:
            return 0
        return therapist.associated_patients.filter_by(role='jugador', is_active=True).count()

    @staticmethod
    def save(user):
        db.session.add(user)
        db.session.commit()
        return user
