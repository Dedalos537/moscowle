from ..repositories.user_repository import UserRepository
from ..extensions import db, bcrypt
from ..errors import NotFoundError, ConflictError


class UserService:
    def __init__(self):
        self.repo = UserRepository(db.session)

    def get_by_email(self, email: str):
        user = self.repo.find_by_email(email)
        if not user:
            raise NotFoundError(f"User with email {email} not found")
        return user

    def create_admin_if_missing(self, email: str, password: str):
        existing = self.repo.find_by_email(email)
        if existing:
            return existing

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = self.repo.create(email=email, password_hash=password_hash, role_id=1)
        db.session.commit()
        return user

    def verify_password(self, user, password: str) -> bool:
        return bcrypt.check_password_hash(user.password_hash, password)

    def create_user(self, email: str, password: str, role_id: int = None):
        existing = self.repo.find_by_email(email)
        if existing:
            raise ConflictError(f"User with email {email} already exists")
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = self.repo.create(email=email, password_hash=password_hash, role_id=role_id)
        db.session.commit()
        return user
