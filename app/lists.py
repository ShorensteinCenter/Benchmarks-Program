import requests
import pandas as pd
from pandas.io.json import json_normalize
import asyncio
from aiohttp import ClientSession, BasicAuth
import json
import iso8601
from datetime import datetime, timezone, timedelta

class MailChimpList():

	# The max size of a request to the MailChimp API
	CHUNK_SIZE = 15000

	# The number of simultaneous connections accepted by the API
	MAX_CONNECTIONS = 5

	def __init__(self, id, members, unsubscribes, cleans, api_key, data_center):
		self.id = id
		self.members = int(members)
		self.unsubscribes = int(unsubscribes)
		self.cleans = int(cleans)
		self.list_size = self.members + self.unsubscribes + self.cleans
		self.api_key = api_key
		self.data_center = data_center

		# The number of requests to make
		# If list contains less than CHUNK_SIZE members, this is 1 request
		self.number_of_chunks = 1 if self.members < self.CHUNK_SIZE else self.members // self.CHUNK_SIZE + 1

	# Calculates pct of members, unsubscribes, and cleans
	def calc_list_breakdown(self):
		self.member_pct = "{:.2%}".format(self.members/self.list_size)
		self.unsubscribe_pct = "{:.2%}".format(self.unsubscribes/self.list_size)
		self.clean_pct = "{:.2%}".format(self.cleans/self.list_size)

	# Imports information about all list members from the MailChimp API 3.0
	def import_list_data(self):

		# A temporary list to store total results in
		members_list = []

		for x in range(0, self.number_of_chunks):
			
			# Calculate the size of this chunk
			chunk = self.members % self.CHUNK_SIZE if x == self.number_of_chunks - 1 else self.CHUNK_SIZE

			# Calculate where in the mailing list to begin request from
			offset = x * self.CHUNK_SIZE

			params = (
				('fields', 'members.status,members.timestamp_opt,members.timestamp_signup,members.stats,members.id'),
				('count', chunk),
				('offset', offset),
				('status', 'subscribed'),
			)

			request_uri = 'https://' + self.data_center + '.api.mailchimp.com/3.0/lists/' + self.id +'/members'
			response = requests.get(request_uri, params=params, auth=('shorenstein', self.api_key))
			
			if response.status_code != 200:
				raise ConnectionError(str(response.status_code) + ': ' + response.reason)

			# Add the request response to total results
			members_list += response.json()['members']

		# Create a pandas dataframe and store members info
		self.df = pd.DataFrame(members_list)

	# Calculates the percentage of members who open greater than 80% of the time
	def calc_high_open_rate_pct(self):

		# Extract member stats from nested json and store them in a flattened dataframe
		stats = json_normalize(self.df['stats'].tolist())

		# Merge the stats dataframe with the rest of the original dataframe
		self.df = self.df[['status', 'timestamp_opt', 'timestamp_signup', 'id']].join(stats)

		# Sum the number of rows where average open rate exceeds 0.8
		# Then divide by the total number of rows
		self.high_open_rate_pct = sum(x > 0.8 for x in self.df['avg_open_rate']) / self.list_size

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
	async def import_members_async(self, r):
		params = (
			('fields', 'activity.action,activity.timestamp,email_id'),
		)

		request_uri = 'https://' + self.data_center + '.api.mailchimp.com/3.0/lists/' + self.id +'/members/{}/activity'
		
		# List of async tasks to do
		tasks = []

		# Placeholder for gathered async responses
		responses = None

		# Create a semaphore to bound concurrent connections
		sem = asyncio.Semaphore(self.MAX_CONNECTIONS)

		# Create a session with which to make requests
		async with ClientSession() as session:
			for x in range(r):

				member_id = self.member_list[x]

				# Add a new import task to the queue for each list member
				task = asyncio.ensure_future(self.fetch_member_activity_sem(sem, 
					request_uri.format(member_id), params, session))
				tasks.append(task)

			# Await completion of all requests and gather results
			responses = await asyncio.gather(*tasks)

		# Calculate timestamp for one year ago
		now = datetime.now(timezone.utc)
		one_year_ago = now - timedelta(days=365)

		# Flatten responses
		# Filter out activity that is not an open within the last year
		activities = [{**{'id': response['email_id']}, 
			**{'action_': d 
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

		# Create a list of unique ids
		self.member_list = self.df['id'].tolist()

		# Async tasks with asyncio
		loop = asyncio.get_event_loop()
		future = asyncio.ensure_future(self.import_members_async(len(self.member_list)))
		loop.run_until_complete(future)


