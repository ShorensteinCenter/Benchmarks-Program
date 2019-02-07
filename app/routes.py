"""This module contains all routes for the web app."""
import hashlib
import json
import requests
from titlecase import titlecase
import iso8601
import pandas as pd
from sqlalchemy import desc
from flask import render_template, jsonify, session, request, abort
from wtforms.fields.core import BooleanField
from app import app, db
from app.forms import UserForm, OrgForm, ApiKeyForm
from app.models import AppUser, Organization, EmailList, ListStats
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

@app.route('/faq')
def faq():
    """FAQ route."""

    # Get information about organizations
    orgs_with_lists = pd.read_sql(
        Organization.query.join(EmailList).filter_by(store_aggregates=True)
        .with_entities(Organization.financial_classification,
                       Organization.coverage_scope,
                       Organization.coverage_focus,
                       Organization.platform,
                       Organization.employee_range,
                       Organization.budget)
        .statement,
        db.session.bind)
    financial_classifications = {
        k: '{:.0%}'.format(v) for k, v in
        dict(orgs_with_lists['financial_classification'].value_counts(
            normalize=True)).items()}
    coverage_scopes = {
        k: '{:.0%}'.format(v) for k, v in
        dict(orgs_with_lists['coverage_scope'].value_counts(
            normalize=True)).items()}
    coverage_focuses = {
        k: '{:.0%}'.format(v) for k, v in
        dict(orgs_with_lists['coverage_focus'].value_counts(
            normalize=True)).items()}
    platforms = {
        k: '{:.0%}'.format(v) for k, v in
        dict(orgs_with_lists['platform'].value_counts(
            normalize=True)).items()}
    employees = {
        k: '{:.0%}'.format(v) for k, v in
        dict(orgs_with_lists['employee_range'].value_counts(
            normalize=True)).items()}
    budgets = {
        k: '{:.0%}'.format(v) for k, v in
        dict(orgs_with_lists['budget'].value_counts(
            normalize=True)).items()}

    # Get information about lists
    lists_allow_aggregation = pd.read_sql(
        ListStats.query.filter(ListStats.list.has(store_aggregates=True))
        .order_by('list_id', desc('analysis_timestamp'))
        .distinct(ListStats.list_id)
        .with_entities(ListStats.subscribers, ListStats.open_rate).statement,
        db.session.bind)
    sample_size = '{:,.0f}'.format(len(lists_allow_aggregation))
    subscribers = {
        'mean': '{:,.0f}'.format(lists_allow_aggregation['subscribers'].mean()),
        'max': '{:,.0f}'.format(lists_allow_aggregation['subscribers'].max()),
        'min': '{:,.0f}'.format(lists_allow_aggregation['subscribers'].min()),
        'med': '{:,.0f}'.format(lists_allow_aggregation['subscribers'].median()),
        'std': '{:,.0f}'.format(lists_allow_aggregation['subscribers'].std())
    }
    open_rate = {
        'mean': '{:.1%}'.format(lists_allow_aggregation['open_rate'].mean()),
        'mean_as_pct': round(lists_allow_aggregation['open_rate'].mean() * 100, 1),
        'max': '{:.1%}'.format(lists_allow_aggregation['open_rate'].max()),
        'min': '{:.1%}'.format(lists_allow_aggregation['open_rate'].min()),
        'med': '{:.1%}'.format(lists_allow_aggregation['open_rate'].median()),
        'std': '{:.1%}'.format(lists_allow_aggregation['open_rate'].std())
    }
    return render_template(
        'faq.html',
        financial_classifications=financial_classifications,
        coverage_scopes=coverage_scopes,
        coverage_focuses=coverage_focuses,
        platforms=platforms,
        employees=employees,
        budgets=budgets,
        sample_size=sample_size,
        subscribers=subscribers,
        open_rate=open_rate)

@app.route('/confirmation')
def confirmation():
    """Generic confirmation page route."""
    title = request.args.get('title')
    body = request.args.get('body')
    if not title or not body:
        abort(404)
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
    Checks whether the user and/or organization are already present in the
    database. If the organization exists, create or update the user such
    that they are affiliated with the organization. If the user already exists
    and is approved for access, re-send them an email containing their access
    link.
    If the organization does not exist, store the user's data in the session
    so that it can be used later (see validate_org_info())

    Returns:
        A json containing either the form's errors (if form does not
        validate) or information about what happened (i.e. was the org
        new or existing, was the user new or existing, etc.).
    """
    user_form = UserForm()
    if user_form.validate_on_submit():
        user_org = titlecase(user_form.news_org.data)
        user_name = user_form.name.data.title()
        email_hash = (hashlib.md5(
            user_form.email.data.encode()).hexdigest())
        user_email = user_form.email.data

        # See if the user already exists
        existing_user = AppUser.query.filter_by(email=user_email).first()

        # See if the organization already exists
        existing_org = Organization.query.filter_by(name=user_org).first()

        # If the user selected an organization we're already tracking
        # Add or update that user with a link to the organization
        if existing_org:
            if existing_user:
                existing_user.name = user_name
                existing_user.orgs.append(existing_org)
                db.session.commit()

                # If the user exists, and was already approved for access
                # Re-send them the email containing their access link
                if existing_user.approved:
                    send_activated_email.delay(user_email, email_hash)

            else:
                store_user(user_name, user_email, email_hash, existing_org)

            return jsonify({'org': 'existing',
                            'user': ('approved'
                                     if existing_user
                                     and existing_user.approved
                                     else 'other')})

        # If we're not already tracking the organization, add the user's data
        # to the session to store later once they've told us about the org
        session['user_name'] = user_name
        session['email'] = user_form.email.data
        session['email_hash'] = email_hash
        session['org'] = user_org
        return jsonify({'org': 'new'})

    return jsonify(user_form.errors), 422

@app.route('/org-info')
def org_info():
    """Organization form route.

    Returns a 403 if the user hasn't already submitted the basic info form.
    """
    session_params = ['user_name', 'email', 'email_hash', 'org']
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

        # Create a list of strings from the affiliation checkboxes
        # and the "Other" affiliation input field
        affiliations = [*[elt.label.text
                          for elt in org_form
                          if isinstance(elt, BooleanField)
                          and elt.data
                          and elt.label.text != 'Other'],
                        *([org_form.other_affiliation_name.data]
                          if org_form.other_affiliation_name.data
                          else [])]
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
        user = store_user(session['user_name'], session['email'],
                          session['email_hash'], org)
        if user.approved:
            send_activated_email.delay(user.email, user.email_hash)
        return jsonify({'user': 'approved'
                                if user and user.approved
                                else 'other'})
    return jsonify(org_form.errors), 422

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
    num_orgs = len(orgs_list)
    api_key_form = ApiKeyForm()

    # Don't include an empty select field if there is only one option
    api_key_form.organization.choices = (
        [*[('', '')], *orgs_list]
        if num_orgs > 1
        else orgs_list)
    return render_template(
        'enter-api-key.html', api_key_form=api_key_form, num_orgs=num_orgs)

@app.route('/validate-api-key', methods=['POST'])
def validate_api_key():
    """Validates an API key submitted via POST."""
    api_key_form = ApiKeyForm()
    api_key_form.organization.choices = session['orgs_list']
    if api_key_form.validate_on_submit():
        session['org_id'] = api_key_form.organization.data
        return jsonify(True)
    return jsonify(api_key_form.errors), 422

@app.route('/select-list')
def select_list():
    """Select MailChimp List route."""
    if 'user_id' not in session or 'key' not in session:
        abort(403)
    return render_template('select-list.html')

@app.route('/get-list-data')
def get_list_data():
    """Returns data about the user's MailChimp lists.

    Makes a request to the MailChimp API for details
    about each list. Returns the data as JSON or None
    if there are no lists.
    """
    if 'user_id' not in session or 'key' not in session:
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
                 'creation_timestamp': content['date_created'],
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
    user = AppUser.query.filter_by(id=user_id).first()
    new_status = not user.approved
    user.approved = new_status
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise
    if new_status:
        send_activated_email.delay(user.email, user.email_hash)
    return jsonify(True)
