from flask import session
import requests
import pandas as pd
from pandas.io.json import json_normalize
import asyncio
from aiohttp import ClientSession, BasicAuth
import json

class MailChimpList():

	def __init__(self, id, list_size):
		self.id = id
		self.list_size = int(list_size)
		
		# The max size of a request to the MailChimp API
		self.chunk_size = 15000

		# The number of requests to make
		# If list contains less than chunk_size members, this is 1 request
		self.number_of_chunks = 1 if self.list_size < self.chunk_size else self.list_size // self.chunk_size + 1

	# Imports information about all list members from the MailChimp API 3.0
	def import_list_data(self):

		# A temporary list to store total results in
		members_list = []

		for x in range(0, self.number_of_chunks):
			
			# Calculate the size of this chunk
			chunk = self.list_size % self.chunk_size if x == self.number_of_chunks - 1 else self.chunk_size

			# Calculate where in the mailing list to begin request from
			offset = x * self.chunk_size

			params = (
				('fields', 'members.status,members.timestamp_opt,members.timestamp_signup,members.stats,members.id'),
				('count', chunk),
				('offset', offset),
			)

			request_uri = 'https://' + session['data_center'] + '.api.mailchimp.com/3.0/lists/' + self.id +'/members'
			response = requests.get(request_uri, params=params, auth=('shorenstein', session['key']))
			
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
		self.df_flattened = self.df[['status', 'timestamp_opt', 'timestamp_signup', 'id']].join(stats)

		# Sum the number of rows where average open rate exceeds 0.8
		# Then divide by the total number of rows
		self.high_open_rate_pct = sum(x > 0.8 for x in self.df_flattened['avg_open_rate']) / self.list_size

	# Asynchronously imports member activity for a single member
	async def fetch_member_activity(self, url, params, client_session):
		async with client_session.get(url, params=params, auth=BasicAuth('shorenstein', session['key'])) as response:
			return await response.text()

	# Semaphore getter/context manager
	# Converts response to dict and appends member id for processing
	async def fetch_member_activity_sem(self, sem, url, params, client_session):
		async with sem:
			return json.loads(await self.fetch_member_activity(url, params, client_session))

	# Asynchronously runs the import of member data
	async def import_members_async(self, r):
		params = (
			('fields', 'activity.action,activity.timestamp,email_id'),
		)

		request_uri = 'https://' + session['data_center'] + '.api.mailchimp.com/3.0/lists/' + self.id +'/members/{}/activity'
		
		# List of async tasks to do
		tasks = []

		# Create a semaphore
		# MailChimp's API only supports 10 concurrent connections
		sem = asyncio.Semaphore(10)

		# Create a session with which to make requests
		async with ClientSession() as client_session:
			for x in range(r):

				member_id = self.member_list[x]

				# Pass the session and the semaphore to the request helper
				task = asyncio.ensure_future(self.fetch_member_activity_sem(sem, request_uri.format(member_id), params, client_session))
				tasks.append(task)

			# Await completion of all requests
			responses = await asyncio.gather(*tasks)

			# Create a new dataframe to hold results
			members_activity = pd.DataFrame(responses)
			pd.set_option('display.max_colwidth', 1000)
			print(type(members_activity['activity']))
			print(members_activity['activity'])
			#activity = json_normalize(members_actvity['activity'])
			#print(activity)

	# Imports the recent activity for each list member
	# Merges the recent activity with the list dataframe
	def import_members_activity(self):

		# Create a list of unique ids
		self.member_list = self.df_flattened['id'].tolist()

		# Create an async event loop
		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)
		future = asyncio.ensure_future(self.import_members_async(len(self.member_list)))
		loop.run_until_complete(future)

		# Convert to datetime
		# Merge with 



