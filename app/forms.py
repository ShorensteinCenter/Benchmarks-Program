"""This module declares forms for the HTML templates.

The forms are built using Flask-WTF.
The templates are rendered using Jinja2.
"""
import requests
from flask import session
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Email

class BasicInfoForm(FlaskForm):
    """A form allowing the user to submit their basic information.

    Args:
        Flaskform: the base Flask-WTF form class.
    """
    news_org = StringField('News Organization',
                           validators=[DataRequired()])
    contact_person = StringField('Contact Person',
                                 validators=[DataRequired()])
    email = (StringField('Email Address',
                         validators=[DataRequired(), Email()]))
    newsletters = StringField('Newsletters',
                              validators=[DataRequired()])
    submit = SubmitField('Submit')

class ApiKeyForm(FlaskForm):
    """A form allowing the user to submit their MailChimp API key
    and data storage options.

    Args:
        Flaskform: the base Flask-WTF form class.
    """
    key = StringField('API Key', validators=[DataRequired()])
    store_aggregates = BooleanField('Use my aggregate MailChimp data'
                                    'for benchmarking')
    monthly_updates = BooleanField('I would like to receive monthly'
                                   'benchmarking updates')
    submit = SubmitField('Submit')

    # Validate API key submission
    def validate(self):
        """A custom validation function.

        Submits the API key to MailChimp to make sure it validates.
        If so, uses MailChimp API to discern how many lists the user has
        Finally, stores the information in the session.
        """

        # Default validation (if any), e.g. required fields
        validated = FlaskForm.validate(self)
        if not validated:
            return False

        key = self.key.data

        # Check key contains a data center (i.e. ends with '-usX')
        if '-' not in key:
            self.key.errors.append('Key missing data center')
            return False

        data_center = key.rsplit('-', 1)[1]

        # Get total number of lists
        # If connection refused by server or request fails, bad API key
        request_uri = 'https://{}.api.mailchimp.com/3.0/'.format(data_center)
        params = (
            ('fields', 'total_items'),
        )
        try:
            response = (requests.get(request_uri +
                                     'lists', params=params,
                                     auth=('shorenstein', key)))
        except requests.exceptions.ConnectionError:
            self.key.errors.append('Connection to MailChimp servers'
                                   'refused')
            return False
        if response.status_code != 200:
            self.key.errors.append('MailChimp responded with error '
                                   'code {}'.format(str(response.status_code)))
            return False

        # Store API key, data center, and number of lists in session
        session['key'] = key
        session['data_center'] = data_center
        session['num_lists'] = response.json().get('total_items')
        session['store_aggregates'] = self.store_aggregates.data
        session['monthly_updates'] = self.monthly_updates.data

        return True
