from flask import session
import requests
import json
import pandas as pd

class MailChimpList():

	def __init__(self, id):
		self.id = id
		self.errors = []

	def import_data(self):
		request_uri = 'https://' + session['data_center'] + '.api.mailchimp.com/export/1.0/list/' 
		params = (
			('apikey', session['key']),
			('id', self.id),
		)
		response = requests.get(request_uri, params=params, stream=True)
		if response.status_code != 200:
			self.errors.append('MailChimp export API responded with error code ' + str(response.status_code))
			return False

		for line in response.iter_lines():
			if line:
				decoded_line = line.decode('utf-8')
				print(json.loads(decoded_line))

		return True