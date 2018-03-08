from flask import render_template
from app import app, celery, db, mail
from app.lists import MailChimpList
from app.models import ListStats, AppUser
from app.charts import BarChart
from sqlalchemy.sql.functions import func
from flask_mail import Message

# Does the dirty work of actually pulling in a list
# And storing the resulting calculations in a database
def import_analyze_store_list(list_id, count, open_rate,
	api_key, data_center):
	
	# Create a new list instance and import member data/activity
	mailing_list = MailChimpList(list_id, open_rate,
		count, api_key, data_center)
	mailing_list.import_list_data()

	# Import the subscriber activity as well, and merge
	mailing_list.import_sub_activity()

	# Do the data science shit
	mailing_list.calc_open_rate()
	mailing_list.calc_list_breakdown()
	mailing_list.calc_high_open_rate_pct()
	mailing_list.calc_cur_yr_stats()
	
	# Get list stats
	stats = mailing_list.get_list_stats()

	# Store the stats in database
	list_stats = ListStats(list_id=list_id,
		api_key=api_key,
		data_center=data_center,
		count=count,
		open_rate=stats['open_rate'],
		subscribed_pct=stats['subscribed_pct'],
		unsubscribed_pct=stats['unsubscribed_pct'],
		cleaned_pct=stats['cleaned_pct'],
		pending_pct=stats['pending_pct'],
		high_open_rt_pct=stats['high_open_rt_pct'],
		cur_yr_sub_pct=stats['cur_yr_sub_pct'],
		cur_yr_sub_open_rt=stats['cur_yr_sub_open_rt'])
	db.session.merge(list_stats)
	db.session.commit()

	return stats

# Pull in list data, perform calculations, store results
# Generate charts, email charts to user
@celery.task
def init_list_analysis(list_id, list_name, count,
	open_rate, api_key, data_center, user_email):

	# Try to pull the list stats from database
	existing_list = (ListStats.query.
		filter_by(list_id=list_id).first())

	# Placeholder for list stats
	stats = None

	if existing_list is None:

		stats = import_analyze_store_list(list_id,
			count, open_rate, api_key, data_center)

	else:

		# Get list stats from database results
		stats = {'open_rate': existing_list.open_rate,
			'subscribed_pct': existing_list.subscribed_pct,
			'unsubscribed_pct': existing_list.unsubscribed_pct,
			'cleaned_pct': existing_list.cleaned_pct,
			'pending_pct': existing_list.pending_pct,
			'high_open_rt_pct': existing_list.high_open_rt_pct,
			'cur_yr_sub_pct': existing_list.cur_yr_sub_pct,
			'cur_yr_sub_open_rt': existing_list.cur_yr_sub_open_rt}

	# Log that the request occured
	current_user = AppUser(user_email=user_email,
		list_id=list_id)
	db.session.add(current_user)
	db.session.commit()

	# Generate averages
	avg_stats = db.session.query(func.avg(ListStats.open_rate),
		func.avg(ListStats.subscribed_pct),
		func.avg(ListStats.unsubscribed_pct),
		func.avg(ListStats.cleaned_pct),
		func.avg(ListStats.pending_pct),
		func.avg(ListStats.high_open_rt_pct),
		func.avg(ListStats.cur_yr_sub_pct),
		func.avg(ListStats.cur_yr_sub_open_rt)).first()
	
	# Generate charts
	# Export them as pngs to /charts
	open_rate_chart = BarChart('Avg. Open Rate',
		{'Your List': [stats['open_rate']],
		'Average': [avg_stats[0]]})
	open_rate_chart.render_png(list_id + '_open_rate')

	list_breakdown_chart = BarChart('List Composition',
		{'Subscribed %': [stats['subscribed_pct'], avg_stats[1]],
		'Unsubscribed %': [stats['unsubscribed_pct'], avg_stats[2]],
		'Cleaned %': [stats['cleaned_pct'], avg_stats[3]],
		'Pending %': [stats['pending_pct'], avg_stats[4]]},
		('Your List', 'Average'))
	list_breakdown_chart.render_png(list_id + '_breakdown')

	high_open_rt_pct_chart = BarChart(
		'% of Subscribers with Open Rate >80%',
		{'Your List': [stats['high_open_rt_pct']],
		'Average': [avg_stats[5]]})
	high_open_rt_pct_chart.render_png(list_id + '_high_open_rt')

	cur_yr_member_pct_chart = BarChart(
		'% of Subscribers who Opened an Email in the Last 365 Days',
		{'Your List': [stats['cur_yr_sub_pct']],
		'Average': [avg_stats[6]]})
	cur_yr_member_pct_chart.render_png(list_id + '_cur_yr_memb_pct')

	cur_yr_members_open_rt_chart = BarChart(
		'Avg. Open Rate -\nSubscribers who Opened an Email in the Last 365 Days',
		{'Your List': [stats['cur_yr_sub_open_rt']],
		'Average': [avg_stats[7]]})
	cur_yr_members_open_rt_chart.render_png(
		list_id + '_cur_yr_sub_open_rt')

	# Send charts as an email report
	# Due to the way Flask-Mail works, reimport app_context first
	with app.app_context():
		msg = Message('Your Email List Report is Ready!',
			sender='shorensteintesting@gmail.com',
			recipients=[user_email],
			html=render_template('email.html',
				list_name=list_name, list_id=list_id))
		mail.send(msg)

# Goes through the database and updates all the calculations
# This task is run by Celery Beat
@celery.task
def update_stored_data():

	# Grab what we have in the database
	lists_stats = ListStats.query.with_entities(
		ListStats.list_id,ListStats.count,ListStats.open_rate,
		ListStats.api_key,ListStats.data_center).all()

	# Update each list's calculations in sequence 
	for list_stats in lists_stats:

		import_analyze_store_list(list_stats.list_id, 
			list_stats.count, list_stats.open_rate,
			list_stats.api_key, list_stats.data_center)