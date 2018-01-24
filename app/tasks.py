from app import celery
from app.lists import MailChimpList

@celery.task
def analyze_list(listId, members, unsubscribes, cleans):
	mailing_list = MailChimpList(listId, members, unsubscribes, cleans)
	mailing_list.calc_list_breakdown()
