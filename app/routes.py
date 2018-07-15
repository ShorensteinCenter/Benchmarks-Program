from flask import render_template, jsonify, session, request, redirect, url_for
from app import app, csrf, db
from app.forms import BasicInfoForm, ApiKeyForm
from app.models import AppUser
import requests
from app.tasks import store_user, init_list_analysis, send_activated_email
import hashlib

# Home Page
@app.route('/')
def index():
	return render_template('index.html', methods=['GET'])

# Basic Info Submission Page
@app.route('/basic-info', methods=['GET'])
def basic_info():
	info_form = BasicInfoForm()
	return render_template('basic-form.html', infoForm=info_form)

# Validates posted basic info
@app.route('/validate-basic-info', methods=['POST'])
def validate_basic_info():
	info_form = BasicInfoForm()
	if info_form.validate_on_submit():
		email_hash = (hashlib.md5(
			info_form.email.data.encode()).hexdigest())
		store_user.delay(info_form.news_org.data,
						 info_form.contact_person.data,
						 info_form.email.data,
						 email_hash,
						 info_form.newsletters.data)
		return jsonify(True)
	else:
		return jsonify(info_form.errors), 400

# Post basic-information confirmation page
@app.route('/info-validated', methods=['GET'])
def info_validated():
	return render_template('info-validated.html')

# Validates a posted API key
@app.route('/validateAPIKey', methods=['POST'])
def validate_key():
	form = ApiKeyForm()
	if form.validate_on_submit():
		return jsonify(True)
	else:
		return jsonify(form.errors), 400

# Admin dashboard to approve users
@app.route('/admin', methods=['GET'])
def admin():
	cols = AppUser.__table__.columns.keys()
	users = [[(col, getattr(user_row, col)) for col in cols] 
			 for user_row in AppUser.query.all()]
	return render_template('admin.html', users=users, cols=cols)

# Admin dashboard request to approve a user
@app.route('/activate-user', methods=['GET'])
def activate_user():
	user_id = request.args.get('user')
	result = AppUser.query.filter_by(id=user_id).with_entities(
		AppUser.approved).first()
	new_status = not result.approved
	AppUser.query.filter_by(id=user_id).update({'approved': new_status})
	try:
		db.session.commit()
	except:
		db.session.rollback()
		raise
	if new_status:
		print('sending email')
		send_activated_email.delay(user_id)
	return jsonify(True)

# Secret page for activated users to get started with benchmarking
@app.route('/benchmarks', methods=['GET'])
def benchmarks():
	# If email_hash param is empty, return 403
	result = AppUser.query.with_entities(AppUser.id, AppUser.email,
		AppUser.email_hash).filter_by(email_hash=email_hash).first()
	# If result is none, return 403
	# Else store values in session and render_template

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