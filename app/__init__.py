from flask import Flask
from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery_app import make_celery
from flask_mail import Mail
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)
app.config.from_object(Config)

# Set up logging
formatter = logging.Formatter("[%(asctime)s] "
	"{%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
handler = RotatingFileHandler(
	'benchmarks-log.log', maxBytes=10000000, backupCount=5)
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)
log.addHandler(handler)

csrf = CSRFProtect(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)
celery = make_celery(app)
mail = Mail(app)

from app import routes, models