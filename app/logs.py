"""This module sets up logging."""
import os
import smtplib
import logging
from logging.handlers import RotatingFileHandler, SMTPHandler
from app import app

class SSLSMTPHandler(SMTPHandler):
    """An SMTP handler for logging which allows SSL connections."""
    def emit(self, record):
        """Emits a record."""
        try:
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port)
            msg = self.format(record)
            if self.username:
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
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
    mail_handler = SSLSMTPHandler(
        mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
        fromaddr='shorensteintesting@gmail.com',
        toaddrs=os.environ.get('ADMIN_EMAIL'),
        subject='Application Error',
        credentials=(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD']))

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
