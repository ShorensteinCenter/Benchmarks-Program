from unittest.mock import MagicMock
import pytest
import pandas as pd
from wtforms import BooleanField
from app import app
from app.lists import MailChimpList

@pytest.fixture
def test_app():
    """Sets up a test app."""
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    yield app

@pytest.fixture
def client(test_app):
    """Sets up a test client."""
    with test_app.test_client() as client:
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
        'creation_timestamp': 'quux',
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
def fake_list_stats_query_result_as_df():
    """Provides a Pandas DataFrame containing fake stats as could be extracted
    from the database."""
    yield pd.DataFrame({
        'subscribers': [3, 4, 6],
        'subscribed_pct': [1, 1, 4],
        'unsubscribed_pct': [1, 1, 1],
        'cleaned_pct': [1, 1, 1],
        'pending_pct': [1, 1, 1],
        'open_rate': [0.5, 1, 1.5],
        'high_open_rt_pct': [1, 1, 1],
        'cur_yr_inactive_pct': [1, 1, 1]
    })

@pytest.fixture
def fake_list_stats_query_result_means():
    """Provides a dictionary containing the mean values for the
    fake_list_stats_query_result_as_df() fixture."""
    yield {
        'subscribers': [4],
        'subscribed_pct': [2],
        'unsubscribed_pct': [1],
        'cleaned_pct': [1],
        'pending_pct': [1],
        'open_rate': [1],
        'high_open_rt_pct': [1],
        'cur_yr_inactive_pct': [1]
    }

@pytest.fixture
def mocked_mailchimp_list(mocker, fake_calculation_results):
    """Mocks the MailChimp list class from app/lists.py and attaches fake calculation
    results to the mock attributes."""
    mocked_mailchimp_list = mocker.patch('app.tasks.MailChimpList')
    mocked_mailchimp_list.return_value = MagicMock(**fake_calculation_results)
    yield mocked_mailchimp_list

@pytest.fixture
def mailchimp_list():
    """Creates a MailChimpList. Used for testing class/instance methiods."""
    yield MailChimpList(1, 2, 'foo-bar1', 'bar1')
