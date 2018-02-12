from flask import Flask
from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery_app import make_celery

app = Flask(__name__)
app.config.from_object(Config)
csrf = CSRFProtect(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)
celery = make_celery(app)

from app import routes, models