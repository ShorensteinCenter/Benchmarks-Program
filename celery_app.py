import os
import traceback
from collections import OrderedDict
from celery import Celery
from flask import render_template
from flask_mail import Message

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URI']
    )
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

        def on_failure(self, exc, task_id, args, kwargs, einfo):
            from app import mail
            with app.app_context():
                error_details = OrderedDict(
                    [('Exception', exc),
                     ('Task ID', task_id),
                     ('Args', args),
                     ('Kwargs', kwargs),
                     ('Stack Trace', traceback.format_exception(
                         None, exc, einfo.tb))])
                msg = Message(
                    'Application Error (Celery Task)',
                    sender='shorensteintesting@gmail.com',
                    recipients=[os.environ.get('ADMIN_EMAIL')],
                    html=render_template(
                        'error-email-internal.html',
                        error_details=error_details))
                mail.send(msg)

    celery.Task = ContextTask

    return celery
