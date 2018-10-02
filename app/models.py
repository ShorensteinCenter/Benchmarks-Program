"""This module containes SQLAlchemy models."""
from datetime import datetime
from app import db

# Association table for many-to-many relationship between orgs and users
users = db.Table( # pylint: disable=invalid-name
    'users',
    db.Column('org_id', db.Integer, db.ForeignKey('organization.id'),
              primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('app_user.id'),
              primary_key=True))

# Association table for many-to-many relationship between lists and users
list_users = db.Table( # pylint: disable=invalid-name
    'list_users',
    db.Column('list_id', db.String(64), db.ForeignKey('list_stats.list_id'),
              primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('app_user.id'),
              primary_key=True))

class AppUser(db.Model): # pylint: disable=too-few-public-methods
    """Stores users."""
    id = db.Column(db.Integer, primary_key=True)
    signup_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(64))
    email = db.Column(db.String(64), index=True, unique=True)
    email_hash = db.Column(db.String(64), index=True, unique=True)
    approved = db.Column(db.Boolean)

    def __repr__(self):
        return '<AppUser {}>'.format(self.id)

class ListStats(db.Model): # pylint: disable=too-few-public-methods
    """Stores individual MailChimp lists and their associated stats."""
    list_id = db.Column(db.String(64), primary_key=True)
    list_name = db.Column(db.String(128))
    org_id = db.Column(db.Integer, db.ForeignKey('organization.id',
                                                 name='fk_org_id'))
    api_key = db.Column(db.String(64))
    data_center = db.Column(db.String(64))
    frequency = db.Column(db.Float)
    subscribers = db.Column(db.Integer)
    open_rate = db.Column(db.Float)
    hist_bin_counts = db.Column(db.String(512))
    subscribed_pct = db.Column(db.Float)
    unsubscribed_pct = db.Column(db.Float)
    cleaned_pct = db.Column(db.Float)
    pending_pct = db.Column(db.Float)
    high_open_rt_pct = db.Column(db.Float)
    cur_yr_inactive_pct = db.Column(db.Float)
    store_aggregates = db.Column(db.Boolean)
    monthly_updates = db.Column(db.Boolean)
    monthly_update_users = db.relationship(
        AppUser, secondary=list_users, backref='lists')

    def __repr__(self):
        return '<ListStats {}>'.format(self.list_id)

class Organization(db.Model): # pylint: disable=too-few-public-methods
    """Stores a media or journalism organization."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True, unique=True)
    financial_classification = db.Column(db.String(32))
    coverage_scope = db.Column(db.String(32))
    coverage_focus = db.Column(db.String(64))
    platform = db.Column(db.String(64))
    employee_range = db.Column(db.String(32))
    budget = db.Column(db.String(64))
    affiliations = db.Column(db.String(512))
    lists = db.relationship(ListStats, backref='org')
    users = db.relationship(AppUser, secondary=users, backref='orgs')

    def __repr__(self):
        return '<Organization {}>'.format(self.id)
