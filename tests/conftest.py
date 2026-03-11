import pytest
from app import create_app
from models import db as _db, Annonce

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()

@pytest.fixture
def db_session(app):
    with app.app_context():
        yield _db.session

@pytest.fixture
def client(app):
    return app.test_client()
