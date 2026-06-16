from app.repositories.user_repository import UserRepository


class PatientService:
    def __init__(self):
        self.user_repo = UserRepository()

    def get_therapist_patients(self, therapist_id):
        return self.user_repo.get_all_patients_by_therapist(therapist_id)

    def get_all_active_patients(self):
        from app.models import User

        return User.query.filter_by(role='jugador', is_active=True).order_by(User.username.asc()).all()
