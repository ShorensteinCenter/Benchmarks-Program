from flask import session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email
import requests

class BasicInfoForm(FlaskForm):
	news_org = StringField('News Organization', validators=[DataRequired()])
	contact_person = StringField('Contact Person', validators=[DataRequired()])
	email = (StringField('Email Address', validators=
		[DataRequired(), Email()]))
	newsletters = StringField('Newsletters', validators=[DataRequired()])
	submit = SubmitField('Submit')

class ApiKeyForm(FlaskForm):
	key = StringField('API Key', validators=[DataRequired()])
	store_aggregates = BooleanField('Use my aggregate MailChimp data for benchmarking')
	monthly_updates = BooleanField('I would like to receive monthly benchmarking updates')
	submit = SubmitField('Submit')

	# Validate API key submission 
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

		data_center = key.rsplit('-', 1)[1]

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
			self.key.errors.append(
				'MailChimp responded with error code ' + 
				str(response.status_code))
			return False

		# Store API key, data center, and number of lists in session
		session['key'] = key
		session['data_center'] = data_center
		session['num_lists'] = response.json().get('total_items')
		session['store_aggregates'] = self.store_aggregates.data
		session['monthly_updates'] = self.monthly_updates.data

		return True