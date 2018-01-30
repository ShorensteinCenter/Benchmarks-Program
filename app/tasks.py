from app import celery
from app.lists import MailChimpList

# Celery task to handle list analysis
@celery.task
def analyze_list(list_id, members, unsubscribes, cleans, api_key, data_center):
	mailing_list = MailChimpList(list_id, members, unsubscribes, cleans, api_key, data_center)
	mailing_list.calc_list_breakdown()
	mailing_list.import_list_data()
	mailing_list.calc_high_open_rate_pct()
	mailing_list.import_members_activity()
	print(mailing_list.df)