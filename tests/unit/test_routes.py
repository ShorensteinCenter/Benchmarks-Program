from unittest.mock import MagicMock
import pytest
import pandas as pd
import flask

def test_index(client):
    """Tests the index route."""
    assert client.get('/').status_code == 200

def test_about(client):
    """Tests the about route."""
    assert client.get('/about').status_code == 200

def test_contact(client):
    """Tests the contact route."""
    assert client.get('/contact').status_code == 200

def test_terms(client):
    """Tests the terms route."""
    assert client.get('/terms').status_code == 200

def test_privacy(client):
    """Tests the privacy route."""
    assert client.get('/privacy').status_code == 200

def test_faq(client, mocker):
    """Tests the FAQ route."""
    mocker.patch('app.routes.Organization')
    mocker.patch('app.routes.EmailList')
    mocker.patch('app.routes.db')
    mocker.patch('app.routes.pd.read_sql', side_effect=([
        pd.DataFrame({
            'financial_classification': ['Non-Profit', 'For-Profit', 'B Corp'],
            'coverage_scope': ['Hyperlocal', 'Hyperlocal', 'Hyperlocal'],
            'coverage_focus': ['Single Subject', 'Multiple Subjects', 'Investigative'],
            'platform': ['Digital Only', 'Digital Only', 'Digital Only'],
            'employee_range': ['5 or fewer', '5 or fewer', '5 or fewer'],
            'budget': ['$2m-$10m', '$2m-$10m', '$2m-$10m']
        }),
        pd.DataFrame({
            'subscribers': [1000, 10000, 100000, 20],
            'open_rate': [0.25751, 0.3, 0.45, 1]
        })]))
    mocker.patch('app.routes.ListStats')
    response = client.get('/faq')
    assert response.status_code == 200
    assert ('33% of organizations are non-profits, 33% are for-profits and '
            '33% are B Corps.').encode() in response.data
    assert ('The mean number of subscribers for an email list in our database '
            'is 27,755 with a standard deviation of 48,372.').encode() in response.data
    assert ('The highest open rate is 100.0%, the lowest open rate '
            'is 25.8%').encode() in response.data

@pytest.mark.parametrize('route, status_code', [
    ('/confirmation', 404),
    ('/confirmation?body=foo', 404),
    ('/confirmation?title=bar', 404),
    ('/confirmation?title=foo&body=bar', 200)
])
def test_confirmation(client, route, status_code):
    """Tests the confirmation route."""
    assert client.get(route).status_code == status_code

def test_confirmation_content(client):
    """Tests that the confirmation route renders the title and body."""
    title = 'foo'
    body = 'bar'
    response = client.get('/confirmation?title={}&body={}'.format(title, body))
    assert title.encode() in response.data
    assert body.encode() in response.data

def test_basic_info(client, mocked_userform):
    """Tests the basic info route."""
    assert client.get('/basic-info').status_code == 200
    mocked_userform.assert_called()

def test_validate_basic_info_invalid_form(client, mocked_userform):
    """Tests basic info validation with an invalid UserForm."""
    mocked_userform.return_value.validate_on_submit.return_value = False
    form_errors = {'foo': 'bar'}
    mocked_userform.return_value.errors = form_errors
    response = client.post('/validate-basic-info')
    assert response.status_code == 422
    response_json = response.get_json()
    assert response_json == form_errors

def test_validate_basic_info_new_user(client, mocked_userform, mocker):
    """Tests basic info validation.

    User and organization not present in database.
    """
    mocked_user = mocker.patch('app.routes.AppUser')
    mocked_user.query.filter_by.return_value.first.return_value = None
    mocked_org = mocker.patch('app.routes.Organization')
    mocked_org.query.filter_by.return_value.first.return_value = None
    with client as c:
        response = c.post('/validate-basic-info')
        assert flask.session['user_name'] == 'Foo Bar'
        assert flask.session['email'] == 'foo@bar.com'
        assert flask.session['email_hash'] == (
            'f3ada405ce890b6f8204094deb12d8a8')
        assert flask.session['org'] == 'Foo and a Bar'
        assert response.status_code == 200
        response_json = response.get_json()
        assert response_json['org'] == 'new'

def test_validate_basic_info_existing_org(client, mocked_userform, mocker):
    """Tests basic info validation.

    User is present in the database, organizations is not.
    """
    mocked_user = mocker.patch('app.routes.AppUser')
    mocked_user.query.filter_by.return_value.first.return_value = None
    mocked_org = mocker.patch('app.routes.Organization')
    mocked_org_result = (
        mocked_org.query.filter_by.return_value.first.return_value)
    mocked_store_user = mocker.patch('app.routes.store_user')
    response = client.post('/validate-basic-info')
    mocked_store_user.assert_called_with(
        'Foo Bar', 'foo@bar.com', 'f3ada405ce890b6f8204094deb12d8a8',
        mocked_org_result)
    assert response.status_code == 200
    response_json = response.get_json()
    assert response_json['org'] == 'existing'
    assert response_json['user'] == 'other'

def test_validate_basic_info_existing_user_not_approved(
        client, mocked_userform, mocker):
    """Tests basic info validation.

    User and organization both present in the database.
    The user has not been approved for access.
    """
    mocked_user = mocker.patch('app.routes.AppUser')
    mocked_user_result = (
        mocked_user.query.filter_by.return_value.first.return_value)
    mocked_user_result.approved = False
    mocked_org = mocker.patch('app.routes.Organization')
    mocked_org_result = (
        mocked_org.query.filter_by.return_value.first.return_value)
    mocked_db = mocker.patch('app.routes.db')
    response = client.post('/validate-basic-info')
    mocked_user_result.orgs.append.assert_called_with(mocked_org_result)
    mocked_db.session.commit.assert_called()
    assert response.status_code == 200
    response_json = response.get_json()
    assert response_json['org'] == 'existing'
    assert response_json['user'] == 'other'

def test_validate_basic_info_existing_user_approved(
        client, mocked_userform, mocker):
    """Tests basic info validation.

    User and organization both present in the database.
    The user has been approved for access.
    """
    mocker.patch('app.routes.AppUser')
    mocker.patch('app.routes.Organization')
    mocker.patch('app.routes.db')
    mocked_send_email = mocker.patch('app.routes.send_activated_email')
    response = client.post('/validate-basic-info')
    mocked_send_email.delay.assert_called_with(
        'foo@bar.com', 'f3ada405ce890b6f8204094deb12d8a8')
    assert response.status_code == 200
    response_json = response.get_json()
    assert response_json['org'] == 'existing'
    assert response_json['user'] == 'approved'

@pytest.mark.parametrize('params', [
    ({}),
    ({'email': 'foo@bar.com', 'email_hash': 'foo', 'org': 'bar'}),
    ({'user_name': 'foo', 'email_hash': 'bar', 'org': 'baz'}),
    ({'user_name': 'foo', 'email': 'foo@bar.com', 'org': 'bar'}),
    ({'user_name': 'foo', 'email': 'foo@bar.com', 'email_hash': 'bar'})
])
def test_org_info_bad_session(client, params):
    """Tests the org-info route without proper values stored in the session."""
    with client as c:
        with c.session_transaction() as sess:
            for k, v in params.items():
                sess[k] = v
        assert c.get('/org-info').status_code == 403

def test_org_info(client, mocked_orgform):
    """Tests the org info route."""
    with client as c:
        with c.session_transaction() as sess:
            sess['user_name'] = 'foo'
            sess['email'] = 'foo@bar.com'
            sess['email_hash'] = 'bar'
            sess['org'] = 'baz'
        response = c.get('/org-info')
        mocked_orgform.assert_called()
        assert 'baz'.encode() in response.data

def test_validate_org_info_invalid_form(client, mocked_orgform):
    """Tests org info validation with an invalid OrgForm."""
    mocked_orgform.return_value.validate_on_submit.return_value = False
    form_errors = {'foo': 'bar'}
    mocked_orgform.return_value.errors = form_errors
    response = client.post('/validate-org-info')
    assert response.status_code == 422
    response_json = response.get_json()
    assert response_json == form_errors

def test_validate_org_info(client, mocked_orgform, mocker):
    """Tests org info validation.

    Checks that information is correctly extracted from the OrgForm and
    stored in the database.
    """
    org_details = {
        'name': 'waldo',
        'financial_classification': 'foo',
        'coverage_scope': 'bar',
        'coverage_focus': 'baz',
        'platform': 'qux',
        'employee_range': 'quux',
        'budget': 'quuz',
        'affiliations': '["corge", "garply"]'
    }
    mocked_store_org = mocker.patch('app.routes.store_org')
    mocked_store_user = mocker.patch('app.routes.store_user')
    mocked_store_user.return_value.approved = False
    with client as c:
        with c.session_transaction() as sess:
            sess['user_name'] = 'fred'
            sess['email'] = 'plugh'
            sess['email_hash'] = 'xyzzy'
            sess['org'] = 'waldo'
        c.post('/validate-org-info')
        mocked_store_org.assert_called_with(org_details)
        mocked_store_user.assert_called_with(
            'fred', 'plugh', 'xyzzy', mocked_store_org())

def test_validate_org_info_user_approved(client, mocked_orgform, mocker):
    """Tests org info validation with an approved user."""
    mocker.patch('app.routes.store_org')
    mocked_store_user = mocker.patch('app.routes.store_user')
    mocked_store_user.return_value.approved = True
    mocked_store_user.return_value.email = 'foo@bar.com'
    mocked_store_user.return_value.email_hash = 'foo'
    mocked_send_email = mocker.patch('app.routes.send_activated_email')
    with client as c:
        with c.session_transaction() as sess:
            sess['user_name'] = 'foo'
            sess['email'] = 'bar'
            sess['email_hash'] = 'baz'
            sess['org'] = 'qux'
        response = c.post('/validate-org-info')
        mocked_send_email.delay.assert_called_with('foo@bar.com', 'foo')
        assert response.status_code == 200
        response_json = response.get_json()
        assert response_json['user'] == 'approved'

def test_validate_org_info_user_not_approved(client, mocked_orgform, mocker):
    """Tests org info validation with a user who isn't approved."""
    mocker.patch('app.routes.store_org')
    mocked_store_user = mocker.patch('app.routes.store_user')
    mocked_store_user.return_value.approved = False
    with client as c:
        with c.session_transaction() as sess:
            sess['user_name'] = 'foo'
            sess['email'] = 'bar'
            sess['email_hash'] = 'baz'
            sess['org'] = 'qux'
        response = c.post('/validate-org-info')
        assert response.status_code == 200
        response_json = response.get_json()
        assert response_json['user'] == 'other'

def test_benchmarks_no_user(client):
    """Tests the benchmarks route with no user parameter."""
    response = client.get('/benchmarks')
    assert response.status_code == 404

def test_benchmarks_bad_user(client, mocker):
    """Tests the benchmarks route with an invalid user."""
    mocked_user = mocker.patch('app.routes.AppUser')
    mocked_user.query.filter_by.return_value.first.return_value = None
    response = client.get('/benchmarks/foo')
    assert response.status_code == 403

def test_benchmarks_good_user(client, mocker):
    """Tests the benchmarks route with a good user."""
    mocked_user = mocker.patch('app.routes.AppUser')
    mocked_user_result = (
        mocked_user.query.filter_by.return_value.first.return_value)
    mocked_user_result.id = 1
    mocked_user_result.email = 'foo@bar.com'
    mocked_first_org = MagicMock(id=12345)
    mocked_first_org.name = 'foo'
    mocked_second_org = MagicMock(id=54321)
    mocked_second_org.name = 'bar'
    mocked_user_result.orgs.__iter__.return_value = [
        mocked_first_org, mocked_second_org]
    mocked_api_key_form = mocker.patch('app.routes.ApiKeyForm')
    with client as c:
        response = c.get('/benchmarks/foo')
        mocked_api_key_form.assert_called()
        assert flask.session['user_id'] == 1
        assert flask.session['email'] == 'foo@bar.com'
        assert flask.session['orgs_list'] == [('12345', 'foo'),
                                              ('54321', 'bar')]
        assert response.status_code == 200

def test_validate_api_key_invalid(client, mocker):
    """Tests the validate api key route with an invalid form."""
    mocked_api_key_form = mocker.patch('app.routes.ApiKeyForm')
    mocked_api_key_form.return_value.validate_on_submit.return_value = False
    mocked_api_key_form.return_value.errors = 'foo'
    with client as c:
        with c.session_transaction() as sess:
            sess['orgs_list'] = []
        response = c.post('/validate-api-key')
        assert response.status_code == 422
        response_json = response.get_json()
        assert response_json == 'foo'

def test_validate_api_key_valid(client, mocker):
    """Tests the validate api key route with a valid form."""
    mocked_api_key_form = mocker.patch('app.routes.ApiKeyForm')
    mocked_api_key_form.return_value.validate_on_submit.return_value = True
    mocked_api_key_form.return_value.organization.data = 1
    with client as c:
        with c.session_transaction() as sess:
            sess['orgs_list'] = []
        response = c.post('/validate-api-key')
        assert response.status_code == 200
        assert flask.session['org_id'] == 1
        response_json = response.get_json()
        assert response_json

@pytest.mark.parametrize('sess_values, status_code', [
    ([], 403),
    (['user_id'], 403),
    (['key'], 403),
    (['user_id', 'key'], 200)
])
def test_select_list(client, sess_values, status_code):
    """Tests the select list route."""
    with client as c:
        with c.session_transaction() as sess:
            for sess_value in sess_values:
                sess[sess_value] = 'foo'
        assert c.get('/select-list').status_code == status_code

@pytest.mark.parametrize('sess_value', [
    (None),
    ('user_id'),
    ('key')
])
def test_get_list_data_bad_session(client, sess_value):
    """Tests the get list data route with bad variables in the session."""
    with client as c:
        if sess_value:
            with c.session_transaction() as sess:
                sess[sess_value] = 'foo'
        assert c.get('/get-list-data').status_code == 403

def test_get_list_data(client, mocker):
    """Tests the get list data route."""
    with client as c:
        with c.session_transaction() as sess:
            sess['user_id'] = 1
            sess['key'] = 'foo-bar1'
            sess['data_center'] = 'bar1'
            sess['num_lists'] = 2
        mocked_requests = mocker.patch('app.routes.requests')
        mocked_requests.get.return_value.json.return_value = {'lists': 'foo'}
        response = c.get('/get-list-data')
        mocked_requests.get.assert_called_with(
            'https://bar1.api.mailchimp.com/3.0/lists',
            params=(
                ('fields', 'lists.id,'
                           'lists.name,'
                           'lists.stats.member_count,'
                           'lists.stats.unsubscribe_count,'
                           'lists.stats.cleaned_count,'
                           'lists.stats.open_rate,'
                           'lists.date_created,'
                           'lists.stats.campaign_count'),
                ('count', 2),
            ),
            auth=('shorenstein', 'foo-bar1'))
        assert response.status_code == 200
        response_json = response.get_json()
        assert response_json == 'foo'

def test_analyze_list(client, mocker, fake_list_data):
    """Tests the analyze list route."""
    mocked_request = mocker.patch('app.routes.request')
    fake_list_data['date_created'] = fake_list_data.pop('creation_timestamp')
    mocked_request.get_json.return_value = fake_list_data
    mocked_init_list_analysis = mocker.patch('app.routes.init_list_analysis')
    with client as c:
        with c.session_transaction() as sess:
            sess['user_id'] = 'foo'
            sess['email'] = 'foo@bar.com'
            sess['key'] = 'foo-bar1'
            sess['data_center'] = 'bar1'
            sess['monthly_updates'] = True
            sess['store_aggregates'] = False
            sess['org_id'] = 'bar'
        user_data = {'user_id': sess['user_id'], 'email': sess['email']}
        list_data = {
            'list_id': fake_list_data['list_id'],
            'list_name': fake_list_data['list_name'],
            'key': 'foo-bar1',
            'data_center': 'bar1',
            'monthly_updates': True,
            'store_aggregates': False,
            'total_count': fake_list_data['total_count'],
            'open_rate': fake_list_data['open_rate'],
            'creation_timestamp': fake_list_data['date_created'],
            'campaign_count': fake_list_data['campaign_count']
        }
        response = c.post('/analyze-list')
        mocked_init_list_analysis.delay.assert_called_with(
            user_data, list_data, 'bar')
        assert response.status_code == 200
        response_json = response.get_json()
        assert response_json
