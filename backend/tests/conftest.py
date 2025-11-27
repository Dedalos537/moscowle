import pytest
import os

from app import create_app
from app.extensions import db as _db


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = 'test-secret-key'


@pytest.fixture(scope='session')
def app():
    app = create_app(TestConfig)
    # create all tables
    with app.app_context():
        _db.create_all()
    yield app
    # teardown
    with app.app_context():
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def db(app):
    with app.app_context():
        yield _db
