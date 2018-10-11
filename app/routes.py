"""This module contains all routes for the web app."""
import hashlib
import json
import requests
from titlecase import titlecase
from flask import render_template, jsonify, session, request, abort
from wtforms.fields.core import BooleanField
from app import app, db
from app.forms import UserForm, OrgForm, ApiKeyForm
from app.models import AppUser, Organization
from app.dbops import store_user, store_org
from app.tasks import init_list_analysis, send_activated_email

@app.route('/')
def index():
    """Index route."""
    return render_template('index.html')

@app.route('/about')
def about():
    """About route."""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Contact route."""
    return render_template('contact.html')

@app.route('/terms')
def terms():
    """Terms of Use route."""
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    """Privacy Policy route."""
    return render_template('privacy.html')

@app.route('/confirmation')
def confirmation():
    """Generic confirmation page route."""
    title = request.args.get('title')
    body = request.args.get('body')
    return render_template('confirmation.html', title=title, body=body)

@app.route('/basic-info')
def basic_info():
    """Basic Info Form route."""
    user_form = UserForm()
    return render_template('user-form.html', user_form=user_form)

@app.route('/validate-basic-info', methods=['POST'])
def validate_basic_info():
    """Validates basic info submitted via POST.

    Calls the WTF-Forms validation function.
    If form is valid, calculates the md5-hash of the user's email and
    parses the form data (e.g. titlecase organization names).
    If the user entered an organization already in the database, create a new
    user affiliated with that organization (or update an existing user). If the
    organization is new, store the user's data and the organization data in
    the session for later use.

    Returns:
        A json containing either the form's errors (if form does not
        validate) or information about what happened (i.e. was the org
        new or existing).
    """
    user_form = UserForm()
    if user_form.validate_on_submit():
        user_org = titlecase(user_form.news_org.data)
        user_name = user_form.name.data.title()
        email_hash = (hashlib.md5(
            user_form.email.data.encode()).hexdigest())

        # Generate a list of organization names
        orgs = Organization.query.with_entities(Organization.name).all()
        org_list = [org.name for org in orgs]

        # If the user selected an organization we're already tracking
        # Find the organization and create/update the user
        # With a link to that org
        if user_org in org_list:
            org = Organization.query.filter_by(name=user_org).first()
            store_user(user_name, user_form.email.data, email_hash, org)
            return jsonify({'org': 'existing'})

        # If we're not already tracking the organization, add the user's data
        # to the session to store later once they've told us about the org
        session['name'] = user_name
        session['email'] = user_form.email.data
        session['email_hash'] = email_hash
        session['org'] = user_org
        return jsonify({'org': 'new'})

    return jsonify(user_form.errors), 400

@app.route('/org-info')
def org_info():
    """Organization form route.

    Returns a 403 if the user hasn't already submitted the basic info form.
    """
    session_params = ['name', 'email', 'email_hash', 'org']
    if any(session_param not in session for session_param in session_params):
        abort(403)
    org_form = OrgForm()
    return render_template('org-form.html',
                           org_form=org_form,
                           org=session['org'])

@app.route('/validate-org-info', methods=['POST'])
def validate_org_info():
    """Validates organization info submitted via POST.

    Calls the WTF-Form validation function.
    If the form is valid, stores the organization in the database, then
    stores a new user/updates an existing user such that they are
    affiliated with the organization.
    """
    org_form = OrgForm()
    if org_form.validate_on_submit():
        affiliations = [elt.label.text
                        for elt in org_form
                        if isinstance(elt, BooleanField) and elt.data]
        org_details = {
            'name': session['org'],
            'financial_classification': org_form.financial_classification.data,
            'coverage_scope': org_form.coverage_scope.data,
            'coverage_focus': org_form.coverage_focus.data,
            'platform': org_form.platform.data,
            'employee_range': org_form.employee_range.data,
            'budget': org_form.budget.data,
            'affiliations': json.dumps(affiliations)}
        org = store_org(org_details)
        store_user(session['name'], session['email'], session['email_hash'], org)
        return jsonify(True)
    return jsonify(org_form.errors), 400

@app.route('/benchmarks/<string:user>')
def benchmarks(user):
    """A secret route for activated users.

    Verifies that the md5-hash submitted in the url string
    is in the database and that the corresponding user has been
    approved.
    If not approved, return a 403 error.
    If approved, render the form allowing the user to submit
    their API key.
    """
    result = AppUser.query.filter_by(email_hash=user, approved=True).first()
    if result is None:
        abort(403)
    session['user_id'] = result.id
    session['email'] = result.email

    # Dynamically generate options for the organizations select box
    orgs_list = [(str(org.id), org.name) for org in result.orgs]
    session['orgs_list'] = orgs_list
    api_key_form = ApiKeyForm()
    api_key_form.organization.choices = [*[('', '')], *orgs_list]
    return render_template('enter-api-key.html', api_key_form=api_key_form)

@app.route('/validate-api-key', methods=['POST'])
def validate_api_key():
    """Validates an API key submitted via POST."""
    api_key_form = ApiKeyForm()
    api_key_form.organization.choices = session['orgs_list']
    if api_key_form.validate_on_submit():
        session['org_id'] = api_key_form.organization.data
        return jsonify(True)
    return jsonify(api_key_form.errors), 400

@app.route('/select-list')
def select_list():
    """Select MailChimp List route."""
    if 'user_id' not in session:
        abort(403)
    return render_template('select-list.html')

@app.route('/get-list-data')
def get_list_data():
    """Returns data about the user's MailChimp lists.

    Makes a request to the MailChimp API for details
    about each list. Returns the data as JSON or None
    if there are no lists.
    """
    if 'user_id' not in session:
        abort(403)
    request_uri = ('https://{}.api.mailchimp.com/3.0/lists'.format(
        session['data_center']))
    params = (
        ('fields', 'lists.id,'
                   'lists.name,'
                   'lists.stats.member_count,'
                   'lists.stats.unsubscribe_count,'
                   'lists.stats.cleaned_count,'
                   'lists.stats.open_rate,'
                   'lists.date_created,'
                   'lists.stats.campaign_count'),
        ('count', session['num_lists']),
    )
    print(params)
    response = requests.get(request_uri, params=params,
                            auth=('shorenstein', session['key']))
    data = response.json()['lists'] or None
    return jsonify(data)

@app.route('/analyze-list', methods=['POST'])
def analyze_list():
    """Initiates analysis of the list select by the user.

    Creates dictionaries containing all relevant user/list data required
    to perform analysis, then intiates analysis using a celery task.
    """
    content = request.get_json()
    user_data = {'user_id': session['user_id'],
                 'email': session['email']}
    list_data = {'list_id': content['list_id'],
                 'list_name': content['list_name'],
                 'key': session['key'],
                 'data_center': session['data_center'],
                 'monthly_updates': session['monthly_updates'],
                 'store_aggregates': session['store_aggregates'],
                 'total_count': content['total_count'],
                 'open_rate': content['open_rate'],
                 'date_created': content['date_created'],
                 'campaign_count': content['campaign_count']}
    org_id = session['org_id']
    init_list_analysis.delay(user_data, list_data, org_id)
    return jsonify(True)

@app.route('/admin')
def admin():
    """Admin dashboard route.

    Fetches user data from the database and then flattens it
    into a list of lists of tuples. This enables a Jinja2 template
    to unpack it dynamically.
    """
    cols = AppUser.__table__.columns.keys()
    users = []
    for user_row in AppUser.query.all():

        # Each user's data consists of the organizations they belong to plus
        # the data stored in their database record
        user = [*[('organizations', [org.name for org in user_row.orgs])],
                *[(col, getattr(user_row, col)) for col in cols]]
        users.append(user)
    return render_template('admin.html', users=users,
                           cols=[*['organizations'], *cols])

@app.route('/activate-user')
def activate_user():
    """Activates (or deactivates) a user.

    Gets the current activation status of the user and flips it.
    If the user is now activated, sends them an email with a unique
    link to the /benchmarks route.
    """
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
