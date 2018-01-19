from flask import render_template, jsonify, session, request
from app import app
from app.forms import ApiKeyForm
from app.lists import MailChimpList
import requests

# Home Page
@app.route('/')
def index():
	form = ApiKeyForm()
	return render_template('index.html', form=form)

# Validates a post'ed API key
@app.route('/validateAPIKey', methods=['POST'])
def validateKey():
	form = ApiKeyForm()
	if form.validate_on_submit():
		return jsonify(True)
	else:
		return jsonify(form.errors), 400

# Returns a JSON containing list names and number of members
# Corresponding to most recently validated API key
@app.route('/getLists', methods=['GET'])
def getLists():
	request_uri = 'https://' + session['data_center'] + '.api.mailchimp.com/3.0/'
	params = (
		('fields', 'lists.id,lists.name,lists.stats.member_count,lists.stats.unsubscribe_count,lists.stats.cleaned_count'),
		('count', session['num_lists']),
	)
	response = requests.get(request_uri + 'lists', params=params, auth=('shorenstein', session['key']))
	return jsonify(response.json())

# Takes a list id and imports the list data
@app.route('/analyzeList', methods=['GET'])
def analyzeList():
	mailing_list = MailChimpList(request.args.get('id'), request.args.get('size'))
	if mailing_list.import_data():
		mailing_list.calc_unique_members()
		mailing_list.calc_high_open_rate_pct()
		print(mailing_list.high_open_rate_pct)
		return jsonify(True)
	else:
		return jsonify(mailing_list.errors), 500
