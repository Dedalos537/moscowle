from .base_repository import BaseRepository
from ..models.user import User


class UserRepository(BaseRepository):
    def __init__(self, session):
        super().__init__(User, session)

    def find_by_email(self, email: str):
        return self.find_one(email=email)
from ..models.user import User


def get_user_by_id(user_id: int):
    return User.query.get(user_id)


def get_user_by_username(username: str):
    return User.query.filter_by(username=username).first()
