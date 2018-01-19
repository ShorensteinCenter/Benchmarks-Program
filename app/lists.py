from flask import session
import requests
import pandas as pd
from pandas.io.json import json_normalize

class MailChimpList():

	def __init__(self, id, list_size):
		self.id = id
		self.list_size = int(list_size)
		self.errors = []
		self.chunk_size = 15000

	# Imports information about all list members from the MailChimp API 3.0
	def import_data(self):

		# Calculate number of requests to make
		# If list contains less than chunk_size members, make a single request
		number_of_chunks = 1 if self.list_size < self.chunk_size else self.list_size // self.chunk_size + 1

		# A temporary list to store total results in
		members_list = []

		for x in range(0, number_of_chunks):
			
			# Calculate the size of this chunk
			chunk = self.list_size % self.chunk_size if x == number_of_chunks - 1 else self.chunk_size

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
				self.errors.append('MailChimp export API responded with error code ' + str(response.status_code))
				return False

			# Add the request response to total results
			members_list += response.json()['members']

		# Create a pandas dataframe and store members info
		self.df = pd.DataFrame(members_list)
		
		return True

	# Calculates the number of unique members in the list
	def calc_unique_members(self):
		self.df.drop_duplicates(subset='id')
		self.unique_members = self.df.id.count()

	# Calculates the percentage of members who open greater than 80% of the time
	def calc_high_open_rate_pct(self):

		# Extract member stats from nested json and store them in a flattened dataframe
		stats = json_normalize(self.df['stats'].tolist())

		# Merge the stats dataframe with the rest of the original dataframe
		self.df_flattened = self.df[['status', 'timestamp_opt', 'timestamp_signup', 'id']].join(stats)

		# Sum the number of rows where average open rate exceeds 0.8
		# Then divide by the total number of rows
		self.high_open_rate_pct = sum(x > 0.8 for x in self.df_flattened['avg_open_rate']) / self.unique_members