import os
from celery.schedules import crontab

class Config():
    SECRET_KEY = os.environ.get('SECRET_KEY')
    CELERY_BROKER_URI = (os.environ.get('CELERY_BROKER_URI') or
                         'amqp://guest:guest@localhost:5672/')
    TASK_SERIALIZER = 'json'
    CELERYBEAT_SCHEDULE = {
        'update_stored_data': {
            'task': 'app.tasks.update_stored_data',
            'schedule': crontab(minute='0', hour='0', day_of_month='*'),
            'args': ()
        },
        'send_monthly_reports': {
            'task': 'app.tasks.send_monthly_reports',
            'schedule': crontab(minute='0', hour='0', day_of_month='2'),
            'args': ()
        }
    }
    SQLALCHEMY_DATABASE_URI = (
        os.environ.get('SQLALCHEMY_DATABASE_URI') or
        ('sqlite:///' + os.path.join(
            os.path.abspath(os.path.dirname(__file__)), 'app.db')))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SERVER_NAME = os.environ.get('SERVER_NAME') or '127.0.0.1:5000'
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    SES_REGION_NAME = os.environ.get('SES_REGION_NAME')
    SES_DEFAULT_EMAIL_SOURCE = os.environ.get('SES_DEFAULT_EMAIL_SOURCE')
