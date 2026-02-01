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
        # Use new relationship + fallback for backward compatibility if needed, 
        # but the migration copied data so we can rely on the new table mostly.
        # However, to be safe, let's use the relationship directly.
        therapist = User.query.get(therapist_id)
        if not therapist:
            return []
        
        # 'associated_patients' is the backref from User.therapists
        # It's a dynamic loader, so we can chain filters
        return therapist.associated_patients.filter_by(role='jugador', is_active=True).all()

    @staticmethod
    def get_all_patients_by_therapist(therapist_id):
        therapist = User.query.get(therapist_id)
        if not therapist:
            return []
        return therapist.associated_patients.filter_by(role='jugador').all()

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
