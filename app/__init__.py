import os
import logging
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_talisman import Talisman
from config import Config
from celery_app import make_celery

app = Flask(__name__)
app.config.from_object(Config)

from app import logs

# Set up logging
logs.setup_logging()

# Set up flask-talisman to prevent xss and other attacks
csp = {
    'default-src': '\'self\'',
    'script-src': ['\'self\'', 'cdnjs.cloudflare.com', 'cdn.jsdelivr.net',
                   'www.googletagmanager.com', 'cdn.plot.ly'],
    'style-src': ['\'self\'', 'fonts.googleapis.com',
                  '\'unsafe-inline\'', 'cdn.jsdelivr.net'],
    'font-src': ['\'self\'', 'fonts.gstatic.com'],
    'img-src': ['\'self\'', 'www.google-analytics.com', 'data:']}
Talisman(app, content_security_policy=csp,
         content_security_policy_nonce_in=['script-src'])

csrf = CSRFProtect(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)
celery = make_celery(app)

from app import routes, models
