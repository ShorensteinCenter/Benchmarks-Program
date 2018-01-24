import os

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'test_secret_key'
    CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672/'