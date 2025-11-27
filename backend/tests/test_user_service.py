import pytest

from app.services.user_service import UserService
from app.extensions import db
from app.models.user import User


def test_create_user_and_get_by_email(db, app):
    svc = UserService()

    # create a user
    user = svc.create_user(email='test@example.com', password='strongpassword', role_id=2)
    assert user.id is not None
    assert user.email == 'test@example.com'

    # fetch by email
    fetched = svc.get_by_email('test@example.com')
    assert fetched.id == user.id


def test_create_user_conflict(db, app):
    svc = UserService()
    svc.create_user(email='conflict@example.com', password='pwd123456', role_id=2)

    with pytest.raises(Exception):
        # should raise ConflictError inside create_user
        svc.create_user(email='conflict@example.com', password='pwd123456', role_id=2)


def test_verify_password(db, app):
    svc = UserService()
    user = svc.create_user(email='verify@example.com', password='mypassword', role_id=2)
    assert svc.verify_password(user, 'mypassword') is True
    assert svc.verify_password(user, 'wrong') is False
