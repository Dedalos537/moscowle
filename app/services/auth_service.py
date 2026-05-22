from app.repositories.user_repository import UserRepository
from app.extensions import bcrypt
from flask_login import login_user, logout_user

class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def login(self, email, password):
        user = self.user_repo.get_by_email(email)
        if user and user.is_active and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return True, user
        return False, None

    def logout(self):
        logout_user()

    def validate_credentials(self, email, password):
        user = self.user_repo.get_by_email(email)
        if not user or not user.is_active:
            return False
        return bcrypt.check_password_hash(user.password, password)
