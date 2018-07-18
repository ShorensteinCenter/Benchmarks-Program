from flask import (render_template, jsonify, session, request,
	redirect, url_for, abort)
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
	return render_template('basic-form.html', info_form=info_form)

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

# A generic confirmation page
@app.route('/confirmation', methods=['GET'])
def confirmation():
	title = request.args.get('title')
	body = request.args.get('body')
	return render_template('confirmation.html', title=title, body=body)

# Secret page for activated users to get started with benchmarking
@app.route('/benchmarks/<string:user>', methods=['GET'])
def benchmarks(user):
	result = AppUser.query.with_entities(AppUser.id, AppUser.news_org,
		AppUser.email).filter_by(email_hash=user,
		approved=True).first()
	if result is None:
		abort(403)
	session['id'] = result.id
	session['email'] = result.email
	api_key_form = ApiKeyForm()
	return render_template('enter-api-key.html',
		news_org=result.news_org, api_key_form=api_key_form)

# Validates a posted API key
@app.route('/validate-api-key', methods=['POST'])
def validate_api_key():
	api_key_form = ApiKeyForm()
	if api_key_form.validate_on_submit():
		return jsonify(True)
	else:
		return jsonify(api_key_form.errors), 400

# Displays page containing MailChimp lists to analyze
@app.route('/select-list', methods=['GET'])
def select_list():
	if session['id'] is None:
		abort(403)
	return render_template('select-list.html');

# Returns a JSON containing list names and number of members
# Corresponding to most recently validated API key
@app.route('/get-list-data', methods=['GET'])
def get_list_data():
	if session['id'] is None:
		abort(403)
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
	data = response.json()['lists'] or None
	return jsonify(data)

# Handles list submission
# Uses celery to queue jobs
@app.route('/analyze-list', methods=['POST'])
def analyze_list():
	content = request.get_json()
	session_dict = {k: v for k, v in session.items()}
	init_list_analysis.delay(session_dict,
		content['list_id'],
		content['list_name'],
		content['total_count'],
		content['open_rate'])
	return jsonify(True)

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
		send_activated_email.delay(user_id)
	return jsonify(True)
