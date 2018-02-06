from flask import session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
import requests

class ApiKeyForm(FlaskForm):
	key = StringField('API Key')
	submit = SubmitField('Submit')

	def __init__(self, *args, **kwargs):
		FlaskForm.__init__(self, *args, **kwargs)

	# Validate API Key Submission 
	def validate(self):
		
		# Default validation (if any), e.g. required fields
		rv = FlaskForm.validate(self)
		if not rv:
			return False

		key = self.key.data

		# Check key contains a data center (i.e. ends with '-usX')
		if '-' not in key:
			self.key.errors.append('Key missing data center')
			return False

		data_center = key.split('-')[1]

		# Get total number of lists
		# If connection refused by server or request fails, bad API key
		request_uri = ('https://' + data_center +
			'.api.mailchimp.com/3.0/')
		params = (
			('fields', 'total_items'),
		)
		try:
			response = (requests.get(request_uri +
				'lists', params=params, 
				auth=('shorenstein', key)))
		except requests.exceptions.ConnectionError:
			self.key.errors.append('Connection to MailChimp servers refused')
			return False
		if response.status_code != 200:
			self.key.errors.append('MailChimp responded with error code ' + str(response.status_code))
			return False

		# Store API key, data center, and number of lists in session
		session['key'] = key
		session['data_center'] = data_center
		session['num_lists'] = response.json().get('total_items')

		return True

class EmailForm(FlaskForm):
	key = StringField('Email Address')
	submit = SubmitField('Submit')