import logging
from logging.handlers import RotatingFileHandler
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail
from flask_talisman import Talisman
from config import Config
from celery_app import make_celery

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

# Set up flask-talisman to prevent xss and other attacks
csp = {
    'default-src': '\'self\'',
    'script-src': ['\'self\'', 'cdnjs.cloudflare.com', 'www.googletagmanager.com'],
    'style-src': ['\'self\'', 'fonts.googleapis.com'],
    'font-src': ['\'self\'', 'fonts.gstatic.com'],
    'img-src': ['\'self\'', 'www.google-analytics.com', 'data:'],
}
Talisman(app, content_security_policy=csp,
    content_security_policy_nonce_in=['script-src', 'style-src'])

csrf = CSRFProtect(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)
celery = make_celery(app)
mail = Mail(app)

from app import routes, models
