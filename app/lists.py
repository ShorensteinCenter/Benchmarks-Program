import pandas as pd
import numpy as np
from pandas.io.json import json_normalize
import asyncio
from aiohttp import ClientSession, BasicAuth
import requests
import json
import io
from datetime import datetime, timedelta, timezone
import iso8601
from billiard import current_process
import os

class MailChimpList(object):

	# The max size of a request to the MailChimp API
	# This is for direct requests to the members endpoint
	CHUNK_SIZE = 5000

	# The number of simultaneous connections accepted by the API
	MAX_CONNECTIONS = 7

	# The number of simultanous connections for the activity import phase
	# This number is lower than MAX_CONNECTIONS
	# Otherwise MailChimp will flag as too many requests
	MAX_ACTIVITY_CONNECTIONS = 2

	# The approximate amount of time (in seconds) it takes to cold boot a proxy
	PROXY_BOOT_TIME = 30

	def __init__(self, id, open_rate, count, api_key, data_center):
		self.id = id
		self.open_rate = float(open_rate)
		self.count = int(count)
		self.api_key = api_key
		self.data_center = data_center

	# Asynchronously imports list data for CHUNK_SIZE members
	async def fetch_list_data(self, url, params, session):
		async with session.get(url, params=params, auth=BasicAuth('shorenstein', self.api_key)) as response:
			return await response.text()

	# Make requests with semaphore
	# Convert response to dict for processing
	async def fetch_list_data_sem(self, sem, url, params, session):
		async with sem:
			res = await self.fetch_list_data(url, params, session)
			return json.loads(res)['members']

	# Asynchronously runs the import of basic member data
	async def import_list_async(self, r):

		# MailChimp API endpoint for requests
		request_uri = ('https://' + self.data_center + 
			'.api.mailchimp.com/3.0/lists/' +
			self.id +'/members')

		# List of async tasks to do
		tasks = []

		# Placeholder for async responses
		responses = None

		# Semaphore to limit max simultaneous connections to MailChimp API
		sem = asyncio.Semaphore(self.MAX_CONNECTIONS)

		# Make requests with a single session
		async with ClientSession() as session:
			for x in range(r):
			
				# Calculate the number of members for this request
				chunk = (str(self.count % self.CHUNK_SIZE 
					if x == r - 1 else self.CHUNK_SIZE))

				# Calculate where in the mailing list to begin request from
				offset = str(x * self.CHUNK_SIZE)

				params = (
					('fields', 'members.status,'
						'members.timestamp_opt,'
						'members.timestamp_signup,'
						'members.stats,members.id'),
					('count', chunk),
					('offset', offset),
				)

				# Add a new import task to the queue for each chunk
				task = (asyncio.ensure_future(
					self.fetch_list_data_sem(sem, 
					request_uri, params, session)))
				tasks.append(task)

			# Await completion of all requests and gather results
			responses = await asyncio.gather(*tasks)

		# Flatten the responses into a single list of dicts
		list_data = [response 
			for response_chunk in responses 
			for response in response_chunk]

		# Create a pandas dataframe to store the results
		self.df = pd.DataFrame(list_data)

	# Imports the stats for each list member
	def import_list_data(self):

		# The number of total requests to make to MailChimp
		# If list is smaller than CHUNK_SIZE, this is 1 request
		number_of_requests = (1 if self.count < self.CHUNK_SIZE
			else self.count // self.CHUNK_SIZE + 1)

		# Async tasks with asyncio
		loop = asyncio.get_event_loop()
		future = (asyncio.ensure_future
			(self.import_list_async(number_of_requests)))
		loop.run_until_complete(future)

	# Returns list of md5-hashed email ids for subscribers only
	def get_list_ids(self):
		return self.df[self.df['status'] == 'subscribed']['id'].tolist()

	# Asynchronously imports subscriber activity for a single sub
	async def fetch_sub_activity(self, url, params, session):
		async with session.get(url, params=params, auth=BasicAuth('shorenstein', self.api_key), proxy=self.proxy) as response:
			return await response.text()

	# Make requests with semaphore
	# Convert response to dict for processing
	async def fetch_sub_activity_sem(self, sem, url, params, session):
		async with sem:
			res = await self.fetch_sub_activity(url, params, session)
			return json.loads(res)

	# Asynchronously runs the import of subscriber activity
	async def import_sub_activity_async(self, subscriber_list):
		params = (
			('fields', 'activity.action,activity.timestamp,email_id'),
		)

		request_uri = ('https://' + self.data_center +
			'.api.mailchimp.com/3.0/lists/' +
			self.id +'/members/{}/activity')
		
		# List of async tasks to do
		tasks = []

		# Placeholder for async responses
		responses = None

		# Semaphore to limit max simultaneous connections to MailChimp API
		sem = asyncio.Semaphore(self.MAX_ACTIVITY_CONNECTIONS)

		# We proxy requests using US Proxies to prevent MailChimp blocks
		# Get the worker number for this Celery worker
		# We want each worker to control its corresponding proxy process
		# Note that workers are zero-indexed, proxy procceses are not
		p = current_process()
		proxy_process_number = str(p.index + 1)
		
		# Use the US Proxies API to get the proxy info
		proxy_request_uri = 'http://us-proxies.com/api.php'
		params = (
		    ('api', ''),
		    ('uid', '9557'),
		    ('pwd', os.environ.get('PROXY_AUTH_PWD')),
		    ('cmd', 'rotate'),
		    ('process', proxy_process_number),
		)
		proxy_response = requests.get(proxy_request_uri, params=params)
		proxy_response_vars = proxy_response.text.split(':')
		self.proxy = ('http://' + proxy_response_vars[1] + 
			':' + proxy_response_vars[2])

		# Allow some time for the proxy server to boot up
		await asyncio.sleep(self.PROXY_BOOT_TIME)

		# Create a session with which to make requests
		async with ClientSession() as session:
			for subscriber_id in subscriber_list:

				# Add a new import task to the queue for each list subscriber
				task = asyncio.ensure_future(self
					.fetch_sub_activity_sem(sem,
					request_uri.format(subscriber_id),
					params, session))
				tasks.append(task)

			# Await completion of all requests and gather results
			responses = await asyncio.gather(*tasks)

		# Calculate timestamp for one year ago
		now = datetime.now(timezone.utc)
		one_year_ago = now - timedelta(days=365)

		# Flatten responses
		# Filter out activity older than one year
		activities = [{**{'id': response['email_id']}, 
			**{'recent_open': d['timestamp'] 
			for d in response['activity']
			if d['action'] == 'open' and 
				iso8601.parse_date(d['timestamp']) > one_year_ago}} 
			for response in responses]

		# Convert results to a dataframe
		subscriber_activities = pd.DataFrame(activities)

		# Merge dataframes if any subscribers have recently opened
		# Else add an empty recent_open column to dataframe
		# This allows us to assume that a "recent open" column exists
		if 'recent_open' in subscriber_activities:
			self.df = pd.merge(self.df, 
				subscriber_activities, on='id', how='left')
		else:
			self.df['recent_open'] = np.NaN

	# Imports the recent activity for each list subscriber
	def import_sub_activity(self):

		# Get a list of unique subscriber ids
		subscriber_list = self.get_list_ids()

		# Store the number of subscribers for later
		self.subscribers = len(subscriber_list)

		# Async tasks with asyncio
		loop = asyncio.get_event_loop()
		future = (asyncio.ensure_future(
			self.import_sub_activity_async(subscriber_list)))
		loop.run_until_complete(future)

	# Calculates the open rate
	def calc_open_rate(self):
		self.open_rate = self.open_rate / 100

	# Calculates the list breakdown
	def calc_list_breakdown(self):
		statuses = self.df.status.unique()
		self.subscribed_pct = (0 if 'subscribed' not in statuses
			else self.df.status.value_counts()['subscribed'] /
			self.count)
		self.unsubscribed_pct = (0 if 'unsubscribed' not in statuses
			else self.df.status.value_counts()['unsubscribed'] /
			self.count)
		self.cleaned_pct = (0 if 'cleaned' not in statuses
			else self.df.status.value_counts()['cleaned'] /
			self.count)
		self.pending_pct = (0 if 'pending' not in statuses
			else self.df.status.value_counts()['pending'] /
			self.count)

	# Calculates the percentage of subscribers
	# Who open greater than 80% of the time
	def calc_high_open_rate_pct(self):

		# Extract member stats from nested json
		# Then store them in a flattened dataframe
		stats = json_normalize(self.df['stats'].tolist())

		# Merge the dataframes
		self.df = (self.df[['status', 'timestamp_opt',
			'timestamp_signup', 'id', 'recent_open']].join(stats))

		# Sum the number of rows where average open rate exceeds 0.8
		# And the member is a subscriber
		# Then divide by the total number of rows
		self.high_open_rt_pct = (sum(x > 0.8
			for x in self.df[self.df['status'] == 'subscribed']
			['avg_open_rate']) / self.subscribers)

	# Calculates list size and open rate
	# Only includes subs who have opened an email in the previous year
	def calc_cur_yr_stats(self):
		self.cur_yr_sub_pct = (int(self.df['recent_open']
			.count()) / self.subscribers)
		self.cur_yr_sub_open_rt = (self.df[self.df['recent_open']
			.notnull()]['avg_open_rate'].mean())

		# Catchall for taking mean of NaN values
		if self.cur_yr_sub_open_rt is np.NaN:
			self.cur_yr_sub_open_rt = 0

	# Returns list stats as a dictionary
	def get_list_stats(self):
		stats = {'open_rate': self.open_rate,
			'subscribed_pct': self.subscribed_pct,
			'unsubscribed_pct': self.unsubscribed_pct,
			'cleaned_pct': self.cleaned_pct,
			'pending_pct': self.pending_pct,
			'high_open_rt_pct': self.high_open_rt_pct,
			'cur_yr_sub_pct': self.cur_yr_sub_pct,
			'cur_yr_sub_open_rt': self.cur_yr_sub_open_rt}
		return stats

	# Returns a string buffer containing a CSV of the list data
	def get_list_as_csv(self):
		csv_buffer = io.StringIO()
		self.df.to_csv(csv_buffer, index=False)
		csv_buffer.seek(0)
		return csv_buffer