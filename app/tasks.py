from app import celery
from app.lists import MailChimpList
import boto3

# Pull in basic list data (members, per-member stats, etc.)
# Store basic list data in S3
# Make batch request to MailChimp for each list member's activity
@celery.task
def init_list_analysis(list_id, members, unsubscribes, cleans, api_key, data_center):
	
	# Create a new list instance and import basic data
	mailing_list = (MailChimpList(list_id, 
		members, unsubscribes, cleans, api_key, data_center))
	mailing_list.import_list_data()

	print('starting member import')
	# Import the member activity as well
	mailing_list.import_members_activity()

	# Do data science shit
	mailing_list.calc_list_breakdown()
	mailing_list.calc_high_open_rate_pct()
	mailing_list.calc_cur_yr_stats()
	
	"""
	# Store list data and metadata in S3
	metadata = mailing_list.get_list_metadata()
	csv = mailing_list.get_list_as_csv()
	filename = list_id + '_partial.csv'	
	s3 = boto3.client('s3')
	s3.put_object(Body=csv.getvalue(), Bucket='partialdfs', 
		Key=filename, Metadata=metadata)

	mailing_list.batch_request_memb_act()
	"""

