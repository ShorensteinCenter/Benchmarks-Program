from app import db

class ListStats(db.Model):
	list_id = db.Column(db.String(64), primary_key=True, unique=True)
	api_key = db.Column(db.String(64))
	data_center = db.Column(db.String(64))
	open_rate = db.Column(db.Float)
	member_pct = db.Column(db.Float)
	unsubscribe_pct = db.Column(db.Float)
	clean_pct = db.Column(db.Float)
	high_open_rt_pct = db.Column(db.Float)
	cur_yr_member_pct = db.Column(db.Float)
	cur_yr_members_open_rt = db.Column(db.Float)

	def __repr__(self):
		return '<ListStats {}>'.format(self.list_id)