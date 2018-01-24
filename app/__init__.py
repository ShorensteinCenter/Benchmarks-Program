from flask import Flask
from config import Config
from flask_wtf.csrf import CSRFProtect
from celery_app import make_celery

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)
celery = make_celery(app)

from app import routes