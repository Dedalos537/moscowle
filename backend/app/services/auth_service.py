from ..models.user import User
from ..extensions import db


def create_user(username: str, email: str, password: str) -> User:
    user = User(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def authenticate(username_or_email: str, password: str):
    user = User.query.filter((User.username == username_or_email) | (User.email == username_or_email)).first()
    if user and user.check_password(password):
        return user
    return None
