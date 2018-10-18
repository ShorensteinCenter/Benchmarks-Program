"""This module sets up logging."""
import os
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
import boto3
from app import app

class SESHandler(SMTPHandler):
    """An SMTP handler for logging which uses Amazon SES"""
    def __init__(self, mailhost, fromaddr, toaddrs, subject, aws_config): # pylint: disable=too-many-arguments
        self.aws_config = aws_config
        super().__init__(mailhost, fromaddr, toaddrs, subject)

    def emit(self, record):
        """Emits a record."""
        try:
            ses = boto3.client(
                'ses',
                region_name=self.aws_config['ses_region_name'],
                aws_access_key_id=self.aws_config['aws_access_key_id'],
                aws_secret_access_key=self.aws_config['aws_secret_access_key']
            )
            ses.send_email(
                Source=self.fromaddr,
                Destination={'ToAddresses': self.toaddrs},
                Message={
                    'Subject': {'Data': self.subject},
                    'Body': {
                        'Text': {'Data': self.format(record)}
                    }
                }
            )
        except (KeyboardInterrupt, SystemExit): # pylint: disable=try-except-raise
            raise
        except: # pylint: disable=bare-except
            self.handleError(record)

def setup_logging():
    """Sets up logging for the Flask application."""

    # Create file handler for error/warning/info/debug logs
    file_handler = RotatingFileHandler(
        'benchmarks-log.log', maxBytes=10000000, backupCount=5)

    # Apply format to the log messages
    formatter = logging.Formatter(
        '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    # Set the level according to whether we're debugging or not
    if app.debug:
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.WARN)

    # Create equivalent mail handler
    mail_handler = SESHandler(
        mailhost="",
        fromaddr=app.config['SES_DEFAULT_EMAIL_SOURCE'],
        toaddrs=[os.environ.get('ADMIN_EMAIL')],
        subject='Application Error',
        aws_config={
            'ses_region_name': app.config['SES_REGION_NAME'],
            'aws_access_key_id': app.config['AWS_ACCESS_KEY_ID'],
            'aws_secret_access_key': app.config['AWS_SECRET_ACCESS_KEY']})

    # Set the email format
    mail_handler.setFormatter(logging.Formatter('''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
    '''))

    # Only email errors, not warnings
    mail_handler.setLevel(logging.ERROR)

    # Add the handlers
    loggers = [app.logger, logging.getLogger('sqlalchemy'),
               logging.getLogger('werkzeug')]
    for logger in loggers:
        logger.addHandler(file_handler)
        logger.addHandler(mail_handler)
