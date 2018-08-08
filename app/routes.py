"""This module contains all routes for the web app."""
import hashlib
import requests
from flask import render_template, jsonify, session, request, abort
from app import app, db
from app.forms import BasicInfoForm, ApiKeyForm
from app.models import AppUser
from app.tasks import store_user, init_list_analysis, send_activated_email

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

@app.route('/basic-info')
def basic_info():
    """Basic Info Form route."""
    info_form = BasicInfoForm()
    return render_template('basic-form.html', info_form=info_form)

# Validates posted basic info
@app.route('/validate-basic-info', methods=['POST'])
def validate_basic_info():
    """Validates basic info submitted via POST.

    Calls the WTF-Forms validation function.
    If form is valid, calculate the md5-hash of the user's email.
    Then store that information and return True.
    Else return the form's errors.
    """
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
    return jsonify(info_form.errors), 400

@app.route('/confirmation')
def confirmation():
    """Generic confirmation page route."""
    title = request.args.get('title')
    body = request.args.get('body')
    return render_template('confirmation.html', title=title, body=body)

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
    result = AppUser.query.with_entities(
        AppUser.id, AppUser.news_org, AppUser.email).filter_by(
            email_hash=user, approved=True).first()
    if result is None:
        abort(403)
    session['id'] = result.id
    session['email'] = result.email
    api_key_form = ApiKeyForm()
    return render_template('enter-api-key.html',
                           news_org=result.news_org,
                           api_key_form=api_key_form)

@app.route('/validate-api-key', methods=['POST'])
def validate_api_key():
    """Validates an API key submitted via POST."""
    api_key_form = ApiKeyForm()
    if api_key_form.validate_on_submit():
        return jsonify(True)
    return jsonify(api_key_form.errors), 400

@app.route('/select-list')
def select_list():
    """Select MailChimp List route."""
    if session['id'] is None:
        abort(403)
    return render_template('select-list.html')

@app.route('/get-list-data')
def get_list_data():
    """Returns data about the user's MailChimp lists.

    Makes a request to the MailChimp API for details
    about each list. Returns the data as JSON or None
    if there are no lists.
    """
    if session['id'] is None:
        abort(403)
    request_uri = ('https://{}.api.mailchimp.com/3.0/lists'.format(
        session['data_center']))
    params = (
        ('fields', 'lists.id,'
                   'lists.name,'
                   'lists.stats.member_count,'
                   'lists.stats.unsubscribe_count,'
                   'lists.stats.cleaned_count,'
                   'lists.stats.open_rate'),
        ('count', session['num_lists']),
    )
    response = requests.get(request_uri, params=params,
                            auth=('shorenstein', session['key']))
    data = response.json()['lists'] or None
    return jsonify(data)

@app.route('/analyze-list', methods=['POST'])
def analyze_list():
    """Initiates analysis of the list select by the user.

    Unpacks the user's Werkzeug session into a regular python
    dictionary.
    Passes this dict and the data submitted via POST to a celery
    task.
    """
    content = request.get_json()
    session_dict = {k: v for k, v in session.items()}
    init_list_analysis.delay(session_dict,
                             content['list_id'],
                             content['list_name'],
                             content['total_count'],
                             content['open_rate'])
    return jsonify(True)

# Admin dashboard to approve users
@app.route('/admin')
def admin():
    """Admin dashboard route.

    Fetches user data from the database and then flattens it
    into a list of lists of tuples. This enables a Jinja2 template
    to unpack it dynamically.
    """
    cols = AppUser.__table__.columns.keys()
    users = [[(col, getattr(user_row, col)) for col in cols]
             for user_row in AppUser.query.all()]
    return render_template('admin.html', users=users, cols=cols)

@app.route('/activate-user')
def activate_user():
    """Activates (or deactivates) a user.

    Gets the current activation status of the user and flip it.
    If the user is now activated, send them an email with a unique
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
