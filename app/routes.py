from flask import render_template, jsonify, session, request
from app import app
from app.forms import ApiKeyForm, EmailForm
import requests
from app.tasks import analyze_list

# Home Page
@app.route('/')
def index():
	keyForm = ApiKeyForm()
	emailForm = EmailForm()
	return render_template('index.html', keyForm=keyForm, emailForm=emailForm)

# Validates a post'ed API key
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
	request_uri = 'https://' + session['data_center'] + '.api.mailchimp.com/3.0/'
	params = (
		('fields', 'lists.id,lists.name,lists.stats.member_count,lists.stats.unsubscribe_count,lists.stats.cleaned_count'),
		('count', session['num_lists']),
	)
	response = requests.get(request_uri + 'lists', params=params, auth=('shorenstein', session['key']))
	return jsonify(response.json())

# Handles email address submission
@app.route('/submitEmail', methods=['POST'])
def submit_email():
	form = EmailForm()
	if form.validate_on_submit():
		analyze_list.delay(request.form['listId'], request.form['memberCount'], 
			request.form['unsubscribeCount'], request.form['cleanedCount'], 
			session['key'], session['data_center'])
		return jsonify(True)
	else:
		return jsonify(form.errors), 400

#def analyzeList(listId, members, unsubscribes, cleans):
		#mailing_list.import_members_activity()
		#return jsonify(True)
	#except ConnectionError as e:
		#return jsonify(e), 500
