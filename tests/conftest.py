import os
import tempfile
import string
import random
import pytest
from app import app

@pytest.fixture
def client():
    """Sets up a test client."""
    db_fd, app.config['SQLALCHEMY_DATABASE_URI'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    client = app.test_client()

    yield client

    os.close(db_fd)
    os.unlink(app.config['SQLALCHEMY_DATABASE_URI'])

@pytest.fixture(scope='session')
def random_str_list():
    """Generates a list of 10 random strings, for use in testing."""
    yield [''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
           for x in range(10)]