import pytest
from celery import current_app
from app import app, db

@pytest.fixture
def test_app():
    """Sets up a test app."""
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['NO_EMAIL'] = True
    app.config['SES_DEFAULT_EMAIL_SOURCE'] = 'testing@testing.com'
    current_app.conf.update(CELERY_ALWAYS_EAGER=True)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture
def client(test_app):
    """Sets up a test client."""
    client = test_app.test_client()
    yield client
