import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config(object):
	SECRET_KEY = os.environ.get('SECRET_KEY') or 'test_secret_key'
	CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672/'
	SQLALCHEMY_DATABASE_URI = (os.environ.get('DATABASE_URL') or
		'sqlite:///' + os.path.join(basedir, 'db/app.db'))
	SQLALCHEMY_TRACK_MODIFICATIONS = False
	MAIL_SERVER = 'smtp.gmail.com'
	MAIL_PORT = 465
	MAIL_USE_SSL = True
	MAIL_USERNAME = 'shorensteintesting@gmail.com'
	MAIL_PASSWORD = 'hkshkshks'