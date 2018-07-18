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
from celery.utils.log import get_task_logger
from app import app, mail
from flask import render_template
from flask_mail import Message
from collections import OrderedDict

class MailChimpList(object):

	# The max size of a request to the MailChimp API
	# This is for direct requests to the members endpoint
	CHUNK_SIZE = 5000

	# The number of simultaneous connections we'll make to the API
	# The API limit is 10
	# But we want to make sure we don't interrupt other tasks
	MAX_CONNECTIONS = 4

	# The number of simultanous connections for the activity import phase
	# This number is lower than MAX_CONNECTIONS
	# Otherwise MailChimp will flag as too many requests
	# (Each request takes very little time to complete)
	MAX_ACTIVITY_CONNECTIONS = 2

	# The http status codes we'd like to retry in case of a connection issue
	HTTP_STATUS_CODES_TO_RETRY = [429, 504]

	# The number of times to retry an http request in case of a timeout
	MAX_RETRIES = 3

	# The base backoff time in seconds
	BACKOFF_INTERVAL = 5

	# The approximate amount of seconds it takes to cold boot a proxy
	PROXY_BOOT_TIME = 30

	def __init__(self, id, open_rate, count, api_key, data_center,
		user_email):
		
		self.id = id
		self.open_rate = float(open_rate)
		self.count = int(count)
		self.api_key = api_key
		self.data_center = data_center
		self.user_email = user_email
		self.logger = get_task_logger(__name__)

	# Generic function which can make an async request
	async def make_async_request(self, url, params, session, retry=0):
		
		try:
			
			# Make the async request with aiohttp
			async with session.get(url, params=params, 
				auth=BasicAuth('shorenstein', self.api_key), 
				proxy=self.proxy) as response:

				# If we got a 200 OK, return the request response
				if response.status == 200:
					return await response.text()

				# If we didn't, try to fail gracefully
				else:				
					
					# Always log the bad response
					self.logger.error(
						'Received invalid response code: {} url: {} '
						'API key: {} response: {}'.format(
							response.status, url, 
							self.api_key, response.reason)
						)
					
					# Retry if we got an error
					# And we haven't already retried a few times
					if (response.status in self.HTTP_STATUS_CODES_TO_RETRY 
						and retry < self.MAX_RETRIES):

						# Increment retry count, log, sleep and then retry 
						retry += 1
						self.logger.warning('Retrying ({})'.format(retry))
						await asyncio.sleep(self.BACKOFF_INTERVAL ** retry)
						return await self.make_async_request(url, 
							params, session, retry)

					# In any other case, if this was a user request
					# I.e., not a Celery Beat job
					# Email the user to say something bad happened
					elif self.user_email is not None:
						error_details = OrderedDict([
							('err_desc', 'An error occurred when '
								'trying to import your data from MailChimp.'),
							('mailchimp_err_code', response.status),
							('mailchimp_url', url),
							('api_key', self.api_key),
							('mailchimp_err_reason', response.reason)])
						self.send_error_email(error_details)
					
					# Always raise an exception (to log the stack trace)
					raise ConnectionError()

		# Catch potential timeouts from asyncio rather than MailChimp 
		except asyncio.TimeoutError:
			
			# Log what happened
			self.logger.error('Asyncio request timed out! url: {} '
				'API key: {}'.format(url, self.api_key))

			# Retry if we haven't already retried a few times
			if retry < self.MAX_RETRIES:

				# Increment retry count, log, sleep, and then retry 
				retry += 1
				self.logger.warning('Retrying ({})'.format(retry))
				await asyncio.sleep(self.BACKOFF_INTERVAL ** retry)
				return await self.make_async_request(url, params, session,
					retry)

			# In any other case, if this was a user request
			# I.e., not a Celery Beat job
			# Email the user to say something bad happened
			elif self.user_email is not None:
				error_details = OrderedDict([
					('err_desc', 'An error occurred when '
						'trying to import your data from MailChimp.'),
					('application_exception', 'asyncio.TimeoutError'),
					('mailchimp_url', url),
					('api_key', self.api_key)])
				self.send_error_email(error_details)

			# Reraise the exception (to log the stack trace)
			raise

	# Make requests with semaphore
	# Convert response to dict for processing
	async def fetch_list_data(self, sem, url, params, session):
		async with sem:
			res = await self.make_async_request(url, params, session)
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

		# We proxy requests using US Proxies to prevent MailChimp blocks
		# Get the worker number for this Celery worker
		# We want each worker to control its corresponding proxy process
		# Note that workers are zero-indexed, proxy procceses are not
		p = current_process()

		# Fall back to proxy #1 if we can't ascertain the worker index
		# E.g. in development with only one Celery worker
		try:
			proxy_process_number = str(p.index + 1)
		except AttributeError:
			proxy_process_number = 1
		
		# Use the US Proxies API to get the proxy info
		proxy_request_uri = 'http://us-proxies.com/api.php'
		proxy_params = (
		    ('api', ''),
		    ('uid', '9557'),
		    ('pwd', os.environ.get('PROXY_AUTH_PWD')),
		    ('cmd', 'rotate'),
		    ('process', proxy_process_number),
		)
		proxy_response = requests.get(proxy_request_uri, params=proxy_params)
		proxy_response_vars = proxy_response.text.split(':')

		# Set the proxy for requests from this worker
		# Use the server's IP as a backup
		# Only if we have an issue with the proxy provider
		self.proxy = (None if proxy_response_vars[0] == 'ERROR' 
			else 'http://' + proxy_response_vars[1] + 
			':' + proxy_response_vars[2])

		# Allow some time for the proxy server to boot up
		# We don't need to wait if we're not using a proxy
		if self.proxy:
			await asyncio.sleep(self.PROXY_BOOT_TIME)
		else:
			self.logger.warning('Not using a proxy. Reason: {}'.format(
				proxy_response_vars[0]))

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
					self.fetch_list_data(sem, 
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

	# Make requests with semaphore
	# Convert response to dict for processing
	async def fetch_sub_activity(self, sem, url, params, session):
		async with sem:
			res = await self.make_async_request(url, params, session)
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

		# Create a session with which to make requests
		async with ClientSession() as session:
			for subscriber_id in subscriber_list:

				# Add a new import task to the queue for each list subscriber
				task = asyncio.ensure_future(self
					.fetch_sub_activity(sem,
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

	# Removes nested jsons from the dataframe
	def flatten(self):

		# Extract member stats from nested json
		# Then store them in a flattened dataframe
		stats = json_normalize(self.df['stats'].tolist())

		# Merge the dataframes
		self.df = (self.df[['status', 'timestamp_opt',
			'timestamp_signup', 'id', 'recent_open']].join(stats))

	# Calculates the open rate
	def calc_open_rate(self):
		self.open_rate = self.open_rate / 100

	# Calculates the distribution for subscriber open rate
	def calc_histogram(self):
		bin_boundaries = [-0.001, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.]
		bins = (pd.cut(self.df.loc[self.df['status'] == 
			'subscribed', 'avg_open_rate'], bin_boundaries))
		self.hist_bin_counts = (pd.value_counts(bins, sort=False)
			.apply(lambda x: x / self.subscribers).tolist())

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

		# Sum the number of rows where average open rate exceeds 0.8
		# And the member is a subscriber
		# Then divide by the total number of rows
		self.high_open_rt_pct = (sum(x > 0.8
			for x in self.df[self.df['status'] == 'subscribed']
			['avg_open_rate']) / self.subscribers)

	# Calculates metrics related to activity that occured in the previous year
	def calc_cur_yr_stats(self):
		
		# Total number of subsribers without an open within the last year
		cur_yr_inactive_subs = (self.subscribers - 
			int(self.df['recent_open'].count()))

		# Percent of such subscribers
		self.cur_yr_inactive_pct = cur_yr_inactive_subs / self.subscribers

	# Returns list stats as a dictionary
	def get_list_stats(self):
		stats = {'subscribers': self.subscribers,
			'open_rate': self.open_rate,
			'hist_bin_counts': self.hist_bin_counts,
			'subscribed_pct': self.subscribed_pct,
			'unsubscribed_pct': self.unsubscribed_pct,
			'cleaned_pct': self.cleaned_pct,
			'pending_pct': self.pending_pct,
			'high_open_rt_pct': self.high_open_rt_pct,
			'cur_yr_inactive_pct': self.cur_yr_inactive_pct}
		return stats

	# Returns a string buffer containing a CSV of the list data
	def get_list_as_csv(self):
		csv_buffer = io.StringIO()
		self.df.to_csv(csv_buffer, index=False)
		csv_buffer.seek(0)
		return csv_buffer

	# Sends an error email if something goes wrong
	def send_error_email(self, error_details):
		with app.app_context():
			msg = Message('We Couldn\'t Process Your Email '
				'Benchmarking Report',
				sender='shorensteintesting@gmail.com',
				recipients=[self.user_email],
				html=render_template('error-email.html',
					title='Looks like something went wrong ☹',
					error_details=error_details))
			mail.send(msg)