from ..models.user import User


def get_user_by_id(user_id: int):
    return User.query.get(user_id)


def get_user_by_username(username: str):
    return User.query.filter_by(username=username).first()
