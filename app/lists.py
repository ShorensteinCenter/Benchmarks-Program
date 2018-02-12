import pandas as pd
from pandas.io.json import json_normalize
import asyncio
from aiohttp import ClientSession, BasicAuth
import json
import io
from datetime import datetime, timedelta, timezone
import iso8601

class MailChimpList(object):

	# The max size of a request to the MailChimp API
	# This is for direct requests to the members endpoint
	CHUNK_SIZE = 5000

	# The number of simultaneous connections accepted by the API
	MAX_CONNECTIONS = 10

	# The number of simultanous connections for the activity import phase
	# This number is lower than MAX_CONNECTIONS
	# Otherwise MailChimp will flag as too many requests
	MAX_ACTIVITY_CONNECTIONS = 2

	def __init__(self, id, members, unsubscribes, cleans, api_key, data_center):
		self.id = id
		self.members = int(members)
		self.unsubscribes = int(unsubscribes)
		self.cleans = int(cleans)
		self.api_key = api_key
		self.data_center = data_center

	# Asynchronously imports list data for CHUNK_SIZE members
	async def fetch_list_data(self, url, params, session):
		async with session.get(url, params=params,auth=BasicAuth('shorenstein', self.api_key)) as response:
			return await response.text()

	# Make requests with semaphore
	# Convert response to dict for processing
	async def fetch_list_data_sem(self, sem, url, params, session):
		async with sem:
			res = await self.fetch_list_data(url, params, session)
			return json.loads(res)['members']

	# Asynchronously runs the import of basic list data
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
				chunk = (str(self.members % self.CHUNK_SIZE 
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
					('status', 'subscribed'),
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

	# Imports the recent activity for each list member
	def import_list_data(self):

		# The number of total requests to make to MailChimp
		# If list contains less than CHUNK_SIZE members, this is 1 request
		number_of_requests = (1 if self.members < self.CHUNK_SIZE
			else self.members // self.CHUNK_SIZE + 1)

		# Async tasks with asyncio
		loop = asyncio.get_event_loop()
		future = (asyncio.ensure_future
			(self.import_list_async(number_of_requests)))
		loop.run_until_complete(future)

	# Returns list of md5-hashed email ids
	def get_list_ids(self):
		return self.df['id'].tolist()

	# Asynchronously imports member activity for a single member
	async def fetch_member_activity(self, url, params, session):
		async with session.get(url, params=params, auth=BasicAuth('shorenstein', self.api_key)) as response:
			return await response.text()

	# Make requests with semaphore
	# Convert response to dict for processing
	async def fetch_member_activity_sem(self, sem, url, params, session):
		async with sem:
			res = await self.fetch_member_activity(url, params, session)
			return json.loads(res)

	# Asynchronously runs the import of member data
	async def import_members_async(self, member_list):
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

		# Create a session with which to make requests
		async with ClientSession() as session:
			for member_id in member_list:

				# Add a new import task to the queue for each list member
				task = asyncio.ensure_future(self
					.fetch_member_activity_sem(sem,
					request_uri.format(member_id),
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
		member_activities = pd.DataFrame(activities)

		# Merge dataframes
		self.df = pd.merge(self.df, 
			member_activities, on="id")

	# Imports the recent activity for each list member
	def import_members_activity(self):

		# Get a list of unique ids
		member_list = self.get_list_ids()

		# Async tasks with asyncio
		loop = asyncio.get_event_loop()
		future = (asyncio.ensure_future(
			self.import_members_async(member_list)))
		loop.run_until_complete(future)

	# Calculates pct of members, unsubscribes, and cleans
	def calc_list_breakdown(self):
		self.total_list_size = (self.members + 
			self.unsubscribes + self.cleans)
		self.member_pct = (self.members /
			self.total_list_size)
		self.unsubscribe_pct = (self.unsubscribes /
			self.total_list_size)
		self.clean_pct = (self.cleans /
			self.total_list_size)

	# Calculates the percentage of members
	# Who open greater than 80% of the time
	def calc_high_open_rate_pct(self):

		# Extract member stats from nested json
		# Then store them in a flattened dataframe
		stats = json_normalize(self.df['stats'].tolist())

		# Merge the dataframes
		self.df = (self.df[['status', 'timestamp_opt',
			'timestamp_signup', 'id', 'recent_open']].join(stats))

		# Sum the number of rows where average open rate exceeds 0.8
		# Then divide by the total number of rows
		self.high_open_rt_pct = (sum(x > 0.8
			for x in self.df['avg_open_rate']) / self.total_list_size)

	# Calculates list size and open rate
	# Only includes subs who have opened an email in the previous year
	def calc_cur_yr_stats(self):
		self.cur_yr_members = int(self.df['recent_open'].count())
		self.cur_yr_members_open_rt = (self.df[self.df['recent_open']
			.notnull()]['avg_open_rate'].mean())

	# Returns list stats as a dictionary
	def get_list_stats(self):
		stats = {'member_pct': self.member_pct,
			'unsubscribe_pct': self.unsubscribe_pct,
			'clean_pct': self.clean_pct,
			'high_open_rt_pct': self.high_open_rt_pct,
			'cur_yr_members': self.cur_yr_members,
			'cur_yr_members_open_rt': self.cur_yr_members_open_rt}
		return stats

	# Returns a string buffer containing a CSV of the list data
	def get_list_as_csv(self):
		csv_buffer = io.StringIO()
		self.df.to_csv(csv_buffer, index=False)
		csv_buffer.seek(0)
		return csv_buffer