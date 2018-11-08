import os
import tempfile
from unittest.mock import MagicMock
import pytest
from wtforms import BooleanField
from app import app

@pytest.fixture
def test_app():
    """Sets up a test app."""
    db_fd, app.config['SQLALCHEMY_DATABASE_URI'] = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    yield app

    os.close(db_fd)
    os.unlink(app.config['SQLALCHEMY_DATABASE_URI'])

@pytest.fixture
def client(test_app):
    """Sets up a test client."""
    client = test_app.test_client()
    yield client

@pytest.fixture
def mocked_userform(mocker):
    """Mocks the UserForm. For use in testing application routes."""
    mocked_userform = mocker.patch('app.routes.UserForm')
    mocked_userform.return_value.news_org.data = 'foo and a bar'
    mocked_userform.return_value.name.data = 'foo bar'
    mocked_userform.return_value.email.data = 'foo@bar.com'
    mocked_userform.return_value.validate_on_submit.return_value = True
    yield mocked_userform

@pytest.fixture
def mocked_orgform(mocker):
    """Mocks the OrgForm. For use in testing application routes."""
    mocked_orgform = mocker.patch('app.routes.OrgForm')
    mocked_orgform.return_value.financial_classification.data = 'foo'
    mocked_orgform.return_value.coverage_scope.data = 'bar'
    mocked_orgform.return_value.coverage_focus.data = 'baz'
    mocked_orgform.return_value.platform.data = 'qux'
    mocked_orgform.return_value.employee_range.data = 'quux'
    mocked_orgform.return_value.budget.data = 'quuz'
    mocked_corge_booleanfield = MagicMock(
        spec=BooleanField, data=True, label=MagicMock(text='corge'))
    mocked_other_booleanfield = MagicMock(
        spec=BooleanField, data=True, label=MagicMock(text='Other'))
    mocked_orgform.return_value.__iter__.return_value = [
        mocked_corge_booleanfield, mocked_other_booleanfield]
    mocked_orgform.return_value.other_affiliation_name.data = 'garply'
    mocked_orgform.return_value.validate_on_submit.return_value = True
    yield mocked_orgform

@pytest.fixture
def fake_list_data():
    """Provides a dictionary containing fake data for a MailChimp list."""
    data = {
        'list_id': 'foo',
        'list_name': 'bar',
        'org_id': 1,
        'key': 'foo-bar1',
        'data_center': 'bar1',
        'monthly_updates': False,
        'store_aggregates': False,
        'total_count': 'baz',
        'open_rate': 'qux',
        'date_created': 'quux',
        'campaign_count': 'quuz'
    }
    yield data

@pytest.fixture
def fake_calculation_results():
    """Provides a dictionary containing fake calculation results for a
    MailChimp list."""
    calculation_results = {
        'frequency': 0.1,
        'subscribers': 2,
        'open_rate': 0.5,
        'hist_bin_counts': [0.1, 0.2, 0.3],
        'subscribed_pct': 0.2,
        'unsubscribed_pct': 0.2,
        'cleaned_pct': 0.2,
        'pending_pct': 0.1,
        'high_open_rt_pct': 0.1,
        'cur_yr_inactive_pct': 0.1
    }
    yield calculation_results

@pytest.fixture
def mocked_mailchimp_list(mocker, fake_calculation_results):
    """Mocks the MailChimp list class from app/lists.py and attaches fake calculation
    results to the mock attributes."""
    mocked_mailchimp_list = mocker.patch('app.tasks.MailChimpList')
    for k, v in fake_calculation_results.items():
        setattr(mocked_mailchimp_list.return_value, k, v)
    yield mocked_mailchimp_list
