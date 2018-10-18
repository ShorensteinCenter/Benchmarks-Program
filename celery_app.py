import os
import traceback
from collections import OrderedDict
from celery import Celery

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
            from app.emails import send_email
            error_details = OrderedDict(
                [('Exception', exc),
                 ('Task ID', task_id),
                 ('Args', args),
                 ('Kwargs', kwargs),
                 ('Stack Trace', traceback.format_exception(
                     None, exc, einfo.tb))])
            send_email(
                'Application Error (Celery Task)',
                [os.environ.get('ADMIN_EMAIL')],
                'error-email-internal.html',
                {'error_details': error_details})

    celery.Task = ContextTask

    return celery
