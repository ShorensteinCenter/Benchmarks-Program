from flask import render_template, jsonify, session, request
from app import app, csrf
from app.forms import BasicInfoForm, ApiKeyForm
import requests
from app.tasks import store_current_user, init_list_analysis

# Home Page
@app.route('/')
def index():
	infoForm = BasicInfoForm()
	keyForm = ApiKeyForm()
	return render_template('index.html', infoForm=infoForm,
		keyForm=keyForm)

# Terms Page
@app.route('/terms')
def terms():
	return render_template('terms.html')

# Validates posted basic info
@app.route('/validateBasicInfo', methods=['POST'])
def validate_basic_info():
	form = BasicInfoForm()
	if form.validate_on_submit():
		return jsonify(True)
	else:
		return jsonify(form.errors), 400

# Validates a posted API key
@app.route('/validateAPIKey', methods=['POST'])
def validate_key():
	form = ApiKeyForm()
	if form.validate_on_submit():
		return jsonify(True)
	else:
		return jsonify(form.errors), 400

# Returns a JSON containing list names and number of members
# Corresponding to most recently validated API key
@app.route('/getLists', methods=['GET'])
def get_lists():
	request_uri = ('https://' + session['data_center'] +
		'.api.mailchimp.com/3.0/lists')
	params = (
		('fields', 'lists.id,lists.name,'
			'lists.stats.member_count,'
			'lists.stats.unsubscribe_count,'
			'lists.stats.cleaned_count,'
			'lists.stats.open_rate'),
		('count', session['num_lists']),
	)
	response = (requests.get(request_uri, params=params,
		auth=('shorenstein', session['key'])))
	return jsonify(response.json())

# Handles list submission
# Uses celery to queue jobs
@app.route('/analyzeList', methods=['POST'])
def analyze_list():
	content = request.get_json()
	store_current_user.delay(session['name'],
		session['newsroom'],
		session['email'],
		content['listId'],
		content['listName'])
	init_list_analysis.delay(content['listId'],
		content['listName'],
		content['totalCount'],
		content['openRate'],
		session['key'],
		session['data_center'],
		session['email'])
	return jsonify(True)