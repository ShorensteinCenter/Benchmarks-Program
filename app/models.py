from app import db
from datetime import datetime

class ListStats(db.Model):
	list_id = db.Column(db.String(64), primary_key=True)
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

	def __repr__(self):
		return '<ListStats {}>'.format(self.list_id)

class AppUser(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	timestamp = db.Column(db.DateTime, default=datetime.utcnow)
	user_name = db.Column(db.String(64))
	user_newsroom = db.Column(db.String(64))
	user_email = db.Column(db.String(64))
	list_id = db.Column(db.String(64), index=True)
	list_name = db.Column(db.String(256))

	def __repr__(self):
		return '<AppUser {}>'.format(self.user_email)
