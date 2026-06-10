import secrets

from app.extensions import bcrypt
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def login(self, email, password, remember=False):
        user = self.user_repo.get_by_email(email)
        if user and user.is_active and bcrypt.check_password_hash(user.password, password):
            if user.mfa_enabled:
                return 'mfa_required', user
            return True, user
        return False, None

    def logout(self):
        pass

    def validate_credentials(self, email, password):
        user = self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            return False
        return bcrypt.check_password_hash(user.password, password)
