from flask import render_template, jsonify, session, request
from app import app, csrf
from app.forms import ApiKeyForm, EmailForm
import requests
from app.tasks import init_list_analysis

# Home Page
@app.route('/')
def index():
	keyForm = ApiKeyForm()
	emailForm = EmailForm()
	return render_template('index.html',
		keyForm=keyForm, emailForm=emailForm)

# Terms Page
@app.route('/terms')
def terms():
	return render_template('terms.html')

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

# Handles email address submission
@app.route('/submitEmail', methods=['POST'])
def submit_email():
	form = EmailForm()
	if form.validate_on_submit():
		init_list_analysis.delay(request.form['listId'],
			request.form['listName'],
			request.form['totalCount'],
			request.form['openRate'],
			session['key'],
			session['data_center'],
			form.key.data)
		return jsonify(True)
	else:
		return jsonify(form.errors), 400