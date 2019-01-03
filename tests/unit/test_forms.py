import pytest
import flask
import requests
from app.forms import UserForm, OrgForm, ApiKeyForm

def test_user_form(test_app):
    """Tests the UserForm."""
    with test_app.app_context():
        user_form = UserForm()
        assert isinstance(user_form, UserForm)

@pytest.mark.parametrize('name, email, news_org, expect', [
    ('', 'foo@bar.com', 'foo', False),
    ('foo', '', 'bar', False),
    ('foo', 'foo@', 'bar', False),
    ('foo', 'foo@bar.com', '', False),
    ('foo', 'foo@bar.com', 'bar', True)
])
def test_user_form_validation(test_app, name, email, news_org, expect):
    """Tests the UserForm with different types of parameters."""
    with test_app.app_context():
        user_form = UserForm()
        user_form.name.data = name
        user_form.email.data = email
        user_form.news_org.data = news_org
        assert user_form.validate() == expect

def test_org_form(test_app):
    """Tests the OrgForm."""
    with test_app.app_context():
        org_form = OrgForm()
        assert isinstance(org_form, OrgForm)

@pytest.mark.parametrize(
    'financial_classification, coverage_scope, coverage_focus, platform, '
    'employee_range, budget, expect', [
        ('', '', '', '', '', '', False),
        ('', 'City', 'Investigative', 'Digital Only', '6-10',
         '$2m-$10m', False),
        ('foo', 'City', 'Investigative', 'Digital Only', '6-10',
         '$2m-$10m', False),
        ('B Corp', '', 'Investigative', 'Digital Only', '6-10',
         '$2m-$10m', False),
        ('B Corp', 'City', '', 'Digital Only', '6-10',
         '$2m-$10m', False),
        ('B Corp', 'City', 'Investigative', '', '6-10',
         '$2m-$10m', False),
        ('B Corp', 'City', 'Investigative', 'Digital Only', '',
         '$2m-$10m', False),
        ('B Corp', 'City', 'Investigative', 'Digital Only', '6-10',
         '', False),
        ('B Corp', 'City', 'Investigative', 'Digital Only', '6-10',
         '$2m-$10m', True)])
def test_org_form_validation(test_app, financial_classification,
                             coverage_scope, coverage_focus, platform,
                             employee_range, budget, expect):
    """Tests the OrgForm with different types of parameters."""
    with test_app.app_context():
        org_form = OrgForm()
        org_form.financial_classification.data = financial_classification
        org_form.coverage_scope.data = coverage_scope
        org_form.coverage_focus.data = coverage_focus
        org_form.platform.data = platform
        org_form.employee_range.data = employee_range
        org_form.budget.data = budget
        assert org_form.validate() == expect

def test_api_key_form(test_app):
    """Tests the API Key Form."""
    with test_app.app_context():
        api_key_form = ApiKeyForm()
        assert isinstance(api_key_form, ApiKeyForm)

@pytest.mark.parametrize('key, org_choices, org, expect', [
    ('', [('0', 'foo'), ('1', 'bar')], '0', False),
    ('foo', [], 'bar', False)
])
def test_api_key_form_basic_validation(test_app, key, org_choices, org, expect):
    """Tests the basic validation of the ApiKeyForm."""
    with test_app.app_context():
        api_key_form = ApiKeyForm()
        api_key_form.key.data = key
        api_key_form.organization.choices = org_choices
        api_key_form.organization.data = org
        assert api_key_form.validate() == expect

def test_api_key_form_bad_data_center(test_app):
    """Tests that the ApiKeyForm flags a key without a data center."""
    with test_app.app_context():
        api_key_form = ApiKeyForm()
        api_key_form.key.data = 'foo'
        api_key_form.organization.choices = [('0', 'bar')]
        api_key_form.organization.data = '0'
        assert not api_key_form.validate()
        assert ['Key missing data center'] == list(
            api_key_form.errors.values())[0]

def test_api_key_form_wellformed_request(test_app, mocker):
    """Tests that the request to MailChimp is properly formed."""
    with test_app.app_context():
        api_key_form = ApiKeyForm()
        api_key_form.key.data = 'foo-bar1'
        api_key_form.key.errors = []
        mocked_validate = mocker.patch('app.forms.FlaskForm.validate')
        mocked_validate.return_value = True
        mocked_request = mocker.patch('app.forms.requests')
        api_key_form.validate()
        mocked_request.get.assert_called_with(
            'https://bar1.api.mailchimp.com/3.0/lists',
            params=(('fields', 'total_items'),),
            auth=('shorenstein', 'foo-bar1'))

def test_api_key_form_connection_error(test_app, mocker):
    """Tests that a ConnectionError from MailChimp is handled correctly."""
    with test_app.app_context():
        api_key_form = ApiKeyForm()
        api_key_form.key.data = 'foo-bar1'
        api_key_form.key.errors = []
        mocked_validate = mocker.patch('app.forms.FlaskForm.validate')
        mocked_validate.return_value = True
        mocked_get_request = mocker.patch('app.forms.requests.get')
        mocked_get_request.side_effect = requests.exceptions.ConnectionError()
        assert not api_key_form.validate()
        assert ['Connection to MailChimp servers refused'] == list(
            api_key_form.errors.values())[0]

def test_api_key_form_bad_request(test_app, mocker):
    """Tests that a bad request to MailChimp is handled correctly."""
    with test_app.app_context():
        api_key_form = ApiKeyForm()
        api_key_form.key.data = 'foo-bar1'
        api_key_form.key.errors = []
        mocked_validate = mocker.patch('app.forms.FlaskForm.validate')
        mocked_validate.return_value = True
        mocked_request = mocker.patch('app.forms.requests')
        mocked_request.get.return_value.status_code = 404
        assert not api_key_form.validate()
        assert ['MailChimp responded with error code 404'] == list(
            api_key_form.errors.values())[0]

def test_api_key_form_validates(test_app, mocker):
    """Tests succesful validation of the ApiKeyForm."""
    with test_app.test_request_context():
        api_key_form = ApiKeyForm()
        api_key_form.key.data = 'foo-bar1'
        api_key_form.store_aggregates.data = True
        api_key_form.monthly_updates.data = True
        mocked_validate = mocker.patch('app.forms.FlaskForm.validate')
        mocked_validate.return_value = True
        mocked_request = mocker.patch('app.forms.requests')
        mocked_request.get.return_value.status_code = 200
        mocked_request.get.return_value.json.return_value.get.return_value = 2
        assert api_key_form.validate()
        assert flask.session['key'] == 'foo-bar1'
        assert flask.session['data_center'] == 'bar1'
        assert flask.session['num_lists'] == 2
        assert flask.session['store_aggregates']
        assert flask.session['monthly_updates']
