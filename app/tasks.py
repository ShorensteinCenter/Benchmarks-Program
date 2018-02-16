from app import celery, db
from app.lists import MailChimpList
from app.models import ListStats
from sqlalchemy.sql.functions import func
from app.charts import BarChart

# Pull in list data, perform calculations, then store results
@celery.task
def init_list_analysis(list_id, list_name, members, unsubscribes, cleans, open_rate, api_key, data_center):
	
	# Try to pull the list stats from database
	existing_list = ListStats.query.filter_by(list_id=list_id).first()

	# Placeholder for list stats
	stats = None

	if existing_list is None:

		# Create a new list instance and import basic data
		mailing_list = MailChimpList(list_id, open_rate,
			members, unsubscribes, cleans, api_key, data_center)
		mailing_list.import_list_data()

		# Import the member activity as well
		mailing_list.import_members_activity()

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
			open_rate=stats['open_rate'],
			member_pct=stats['member_pct'],
			unsubscribe_pct=stats['unsubscribe_pct'],
			clean_pct=stats['clean_pct'],
			high_open_rt_pct=stats['high_open_rt_pct'],
			cur_yr_member_pct=stats['cur_yr_member_pct'],
			cur_yr_members_open_rt=stats['cur_yr_members_open_rt'])
		db.session.merge(list_stats)
		db.session.commit()

	else:

		# Get list stats from database results
		stats = {'open_rate': existing_list.open_rate,
			'member_pct': existing_list.member_pct,
			'unsubscribe_pct': existing_list.unsubscribe_pct,
			'clean_pct': existing_list.clean_pct,
			'high_open_rt_pct': existing_list.high_open_rt_pct,
			'cur_yr_member_pct': existing_list.cur_yr_member_pct,
			'cur_yr_members_open_rt': existing_list.cur_yr_members_open_rt}

	# Generate averages
	avg_stats = db.session.query(func.avg(ListStats.open_rate),
		func.avg(ListStats.member_pct),
		func.avg(ListStats.unsubscribe_pct),
		func.avg(ListStats.clean_pct),
		func.avg(ListStats.high_open_rt_pct),
		func.avg(ListStats.cur_yr_member_pct),
		func.avg(ListStats.cur_yr_members_open_rt)).first()
	
	# Generate charts
	open_rate_chart = BarChart('Avg. Open Rate',
		{'Your List': [stats['open_rate']],
		'Average': [avg_stats[0]]})
	open_rate_chart.render_png(list_id + '_open_rate')

	list_breakdown_chart = BarChart('List Breakdown',
		{'Member %': [stats['member_pct'], avg_stats[1]],
		'Unsubscribed %': [stats['unsubscribe_pct'], avg_stats[2]],
		'Cleaned %': [stats['clean_pct'], avg_stats[3]]},
		('Your List', 'Average'))
	list_breakdown_chart.render_png(list_id + '_breakdown')

	high_open_rt_pct_chart = BarChart(
		'% of List Members with Open Rate >80%',
		{'Your List': [stats['high_open_rt_pct']],
		'Average': [avg_stats[4]]})
	high_open_rt_pct_chart.render_png(list_id + '_high_open_rt')

	cur_yr_member_pct_chart = BarChart(
		'% of List Members who Opened an Email in the Last 365 Days',
		{'Your List': [stats['cur_yr_member_pct']],
		'Average': [avg_stats[5]]})
	cur_yr_member_pct_chart.render_png(list_id + 'cur_yr_memb_pct')

	cur_yr_members_open_rt_chart = BarChart(
		'Avg. Open Rate -\nList Members who Opened an Email in the Last 365 Days',
		{'Your List': [stats['cur_yr_members_open_rt']],
		'Average': [avg_stats[6]]})
	cur_yr_members_open_rt_chart.render_png(
		list_id + 'cur_yr_members_open_rt')