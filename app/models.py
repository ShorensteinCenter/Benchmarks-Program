from app import db
from datetime import datetime

class ListStats(db.Model):
	list_id = db.Column(db.String(64), primary_key=True)
	list_name = db.Column(db.String(128))
	user_id = db.Column(db.Integer, db.ForeignKey('app_user.id',
		name='fk_app_user_id'))
	api_key = db.Column(db.String(64))
	data_center = db.Column(db.String(64))
	subscribers = db.Column(db.Integer)
	open_rate = db.Column(db.Float)
	hist_bin_counts = db.Column(db.String(512))
	subscribed_pct = db.Column(db.Float)
	unsubscribed_pct = db.Column(db.Float)
	cleaned_pct = db.Column(db.Float)
	pending_pct = db.Column(db.Float)
	high_open_rt_pct = db.Column(db.Float)
	cur_yr_inactive_pct = db.Column(db.Float)
	monthly_updates = db.Column(db.Boolean)

	def __repr__(self):
		return '<ListStats {}>'.format(self.list_id)

class AppUser(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	signup_timestamp = db.Column(db.DateTime, default=datetime.utcnow)
	news_org = db.Column(db.String(64))
	contact_person = db.Column(db.String(64))
	email = db.Column(db.String(64), index=True, unique=True)
	email_hash = db.Column(db.String(64), index=True, unique=True)
	newsletters = db.Column(db.String(512))
	approved = db.Column(db.Boolean)
	lists = db.relationship(ListStats)

	def __repr__(self):
		return '<AppUser {}>'.format(self.id)
