import logging
import random
import datetime
from collections import OrderedDict
from unittest.mock import call, ANY
from asyncio import TimeoutError as AsyncTimeoutError
import pytest
from aiohttp import ClientHttpProxyError, ServerDisconnectedError
import asynctest
from asynctest import CoroutineMock
import pandas as pd
from pandas.util.testing import assert_frame_equal
import numpy as np
from requests.exceptions import ConnectionError as ConnError
from app.lists import MailChimpImportError

def test_mailchimp_import_error():
    """Tests the custom MailChimp Import Error."""
    error = MailChimpImportError('foo', 'bar')
    assert isinstance(error, MailChimpImportError)
    assert str(error) == 'foo'
    assert error.error_details == 'bar'

@pytest.mark.asyncio
async def test_enable_proxy_no_proxy(mocker, caplog, mailchimp_list):
    """Tests the enable_proxy when the NO_PROXY environment variable is
    present."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [True]
    caplog.set_level(logging.INFO)
    await mailchimp_list.enable_proxy()
    assert mailchimp_list.proxy is None
    assert ('NO_PROXY environment variable set. Not using a proxy.' in
            caplog.text)

@pytest.mark.asyncio
async def test_enable_proxy_successful(mocker, caplog, mailchimp_list):
    """Tests the enable_proxy function."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocked_current_proccess = mocker.patch('app.lists.current_process')
    mocked_current_proccess.return_value.index = 5
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.return_value.text = 'foo:bar:baz'
    caplog.set_level(logging.INFO)
    mocked_sleep = mocker.patch('app.lists.asyncio.sleep', new=CoroutineMock())
    await mailchimp_list.enable_proxy()
    mocked_requests.get.assert_called_with(
        'http://us-proxies.com/api.php',
        params=(
            ('api', ''),
            ('uid', '9557'),
            ('pwd', 'foo'),
            ('cmd', 'rotate'),
            ('process', '6'),
        ),
    )
    assert mailchimp_list.proxy == 'http://bar:baz'
    assert 'Using proxy: http://bar:baz' in caplog.text
    mocked_sleep.assert_called()

@pytest.mark.asyncio
async def test_enable_proxy_unable_to_get_process_number(
        mocker, mailchimp_list):
    """Tests the enable_proxy function when current_process().index
    raises an AttributeError."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocked_current_proccess = mocker.patch('app.lists.current_process')
    del mocked_current_proccess.return_value.index
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.return_value.text = 'foo:bar:baz'
    mocker.patch('app.lists.asyncio.sleep', new=CoroutineMock())
    await mailchimp_list.enable_proxy()
    mocked_requests.get.assert_called_with(
        'http://us-proxies.com/api.php',
        params=(
            ('api', ''),
            ('uid', '9557'),
            ('pwd', 'foo'),
            ('cmd', 'rotate'),
            ('process', '1'),
        ),
    )

@pytest.mark.asyncio
async def test_enable_proxy_proxy_response_error(
        mocker, caplog, mailchimp_list):
    """Tests the enable_proxy function when the request to the proxy provider
    returns an error."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocker.patch('app.lists.current_process')
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.return_value.text = 'ERROR:bar:baz'
    await mailchimp_list.enable_proxy()
    assert mailchimp_list.proxy is None
    assert 'Not using a proxy. Reason: baz.' in caplog.text

@pytest.mark.asyncio
async def test_enable_proxy_connection_error(mocker, caplog, mailchimp_list):
    """Tests the enable_proxy function when the request to the proxy provider
    causes a ConnectionError."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocker.patch('app.lists.current_process')
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.side_effect = ConnError()
    await mailchimp_list.enable_proxy()
    assert mailchimp_list.proxy is None
    assert 'ConnectionError: proxy provider down.' in caplog.text

@pytest.mark.asyncio
async def test_make_async_request(mocker, mailchimp_list):
    """Tests the make_async_request function."""
    client_session_mock = CoroutineMock()
    client_session_mock.get.return_value.__aenter__.return_value.status = 200
    client_session_mock.get.return_value.__aenter__.return_value.text = (
        CoroutineMock(return_value='foo'))
    mocked_basic_auth = mocker.patch('app.lists.BasicAuth')
    async_request_response = await mailchimp_list.make_async_request(
        'www.foo.com', 'foo', client_session_mock)
    client_session_mock.get.assert_called_with(
        'www.foo.com', params='foo',
        auth=mocked_basic_auth('shorenstein', 'foo-bar1'),
        proxy=None)
    assert async_request_response == 'foo'

@pytest.mark.asyncio
async def test_make_async_request_with_status_code_retry(
        mocker, caplog, mailchimp_list):
    """Tests the make_async_request function's retry functionality on a
    bad status code."""
    client_session_mock = CoroutineMock()
    client_session_mock.get.return_value.__aenter__.return_value.reason = 'foo'
    mocker.patch('app.lists.BasicAuth')
    mocked_sleep = mocker.patch('app.lists.asyncio.sleep', new=CoroutineMock())
    status_code = random.choice(mailchimp_list.HTTP_STATUS_CODES_TO_RETRY)
    client_session_mock.get.return_value.__aenter__.return_value.status = (
        status_code)
    with pytest.raises(MailChimpImportError) as e:
        await mailchimp_list.make_async_request(
            'www.foo.com', 'foo', client_session_mock)
        assert e.error_details == OrderedDict([
            ('err_desc', 'An error occurred when trying to import your '
                         'data from MailChimp.'),
            ('mailchimp_err_code', status_code),
            ('mailchimp_url', 'www.foo.com'),
            ('api_key', 'foo-bar1'),
            ('mailchimp_err_reason', 'foo')])
    mocked_sleep.assert_has_calls([
        call(mailchimp_list.BACKOFF_INTERVAL ** x)
        for x in range(1, mailchimp_list.MAX_RETRIES + 1)])
    assert 'Invalid response code from MailChimp' in caplog.text

@pytest.mark.parametrize('error, error_args', [
    (ClientHttpProxyError, ['foo', 'bar']),
    (ServerDisconnectedError, ['foo']),
    (AsyncTimeoutError, ['foo']),
    (ConnectionError, ['foo'])])
@pytest.mark.asyncio
async def test_make_async_request_request_error(
        mocker, caplog, mailchimp_list, error, error_args):
    """Tests the make_async_request function's retry functionality when
    the aiohttp request raises an exception."""
    client_session_mock = CoroutineMock()
    client_session_mock.get.side_effect = error(*error_args)
    mocker.patch('app.lists.BasicAuth')
    mocked_sleep = mocker.patch('app.lists.asyncio.sleep', new=CoroutineMock())
    with pytest.raises(MailChimpImportError) as e:
        await mailchimp_list.make_async_request(
            'www.foo.com', 'foo', client_session_mock)
        assert e.error_details == OrderedDict([
            ('err_desc', 'An error occurred when trying to import '
                         'your data from MailChimp.'),
            ('application_exception', str(error)),
            ('mailchimp_url', 'www.foo.com'),
            ('api_key', 'foo-bar1')])
    mocked_sleep.assert_has_calls([
        call(mailchimp_list.BACKOFF_INTERVAL ** x)
        for x in range(1, mailchimp_list.MAX_RETRIES + 1)])
    assert 'Error in async request to MailChimp' in caplog.text

@pytest.mark.asyncio
async def test_make_async_requests(mocker, mailchimp_list):
    """Tests the make_async_requests function."""
    semaphore_mock = asynctest.MagicMock()
    mocked_make_async_request = mocker.patch(
        'app.lists.MailChimpList.make_async_request', new=CoroutineMock())
    mocked_make_async_request.return_value = '["foo"]'
    assert ['foo'] == await mailchimp_list.make_async_requests(
        semaphore_mock, 'www.foo.com', 'foo', 'bar')
    mocked_make_async_request.assert_called_with(
        'www.foo.com', 'foo', 'bar')

@pytest.mark.asyncio
async def test_import_list_members(mocker, mailchimp_list):
    """Tests the import_list_members function."""
    mocked_enable_proxy = mocker.patch(
        'app.lists.MailChimpList.enable_proxy', new=CoroutineMock())
    mocked_asyncio = mocker.patch('app.lists.asyncio')
    mocked_sem = mocked_asyncio.Semaphore.return_value
    mocked_make_async_requests = mocker.patch(
        'app.lists.MailChimpList.make_async_requests')
    mocked_asyncio.gather = CoroutineMock(return_value=(
        [{'foo': [{'foo': 'bar'}]}, {'bar': [{'foo': 'baz'}]}]))
    mailchimp_list.count = 10020
    await mailchimp_list.import_list_members()
    mocked_enable_proxy.assert_called()
    mocked_asyncio.Semaphore.assert_called_with(mailchimp_list.MAX_CONNECTIONS)
    async_requests_calls_args_list = [
        arg
        for args, _ in mocked_make_async_requests.call_args_list
        for arg in args]
    assert all(
        requests_arg in async_requests_calls_args_list
        for requests_arg in [
            'https://bar1.api.mailchimp.com/3.0/lists/1/members',
            (ANY, ('count', '5000'), ('offset', '0')),
            (ANY, ('count', '5000'), ('offset', '5000')),
            (ANY, ('count', '20'), ('offset', '10000')),
            mocked_sem
        ])
    assert mocked_asyncio.ensure_future.call_count == 3
    args, _ = mocked_asyncio.gather.call_args
    assert len(args) == 3
    fake_df = pd.DataFrame({'foo': ['bar', 'baz']})
    assert_frame_equal(fake_df, mailchimp_list.df)

@pytest.mark.asyncio
@pytest.mark.parametrize('api_results, output_df', [
    ([
        {
            'activity': [{
                'action': 'open',
                'timestamp': '2000-10-1T00:00:00+00:00',
                'campaign_id': 'foo',
                'title': 'bar'
            }],
            'email_id': 'foo',
            'list_id': 'qux'
        },
        {
            'activity': [{
                'action': 'open',
                'timestamp': '1998-1-1T00:00:00+00:00',
                'campaign_id': 'baz',
                'title': 'bar'
            }],
            'email_id': 'bar',
            'list_id': 'qux'
        }],
     pd.DataFrame({
         'id': ['foo', 'bar'],
         'recent_open': ['2000-10-1T00:00:00+00:00', np.NaN]
     })
    ),
    ([
        {
            'activity': [{
                'action': 'open',
                'timestamp': '1997-10-1T00:00:00+00:00',
                'campaign_id': 'foo',
                'title': 'bar'
            }],
            'email_id': 'foo',
            'list_id': 'qux'
        },
        {
            'activity': [{
                'action': 'open',
                'timestamp': '1998-1-1T00:00:00+00:00',
                'campaign_id': 'baz',
                'title': 'bar'
            }],
            'email_id': 'bar',
            'list_id': 'qux'
        }],
     pd.DataFrame({
         'id': ['foo', 'bar'],
         'recent_open': [np.NaN, np.NaN]
     }),
    )
])
async def test_import_sub_activity(
        mocker, mailchimp_list, api_results, output_df):
    """Tests the import_sub_activity function."""
    mocked_asyncio = mocker.patch('app.lists.asyncio')
    mocked_sem = mocked_asyncio.Semaphore.return_value
    mocker.patch('app.lists.MailChimpList.get_list_ids',
                 return_value=['foo', 'bar'])
    mocked_make_async_requests = mocker.patch(
        'app.lists.MailChimpList.make_async_requests')
    mocked_asyncio.gather = CoroutineMock(return_value=api_results)
    mocked_datetime = mocker.patch('app.lists.datetime')
    mocked_datetime.now.return_value = datetime.datetime(
        2001, 1, 1, tzinfo=datetime.timezone.utc)
    mailchimp_list.df = pd.DataFrame({'id': ['foo', 'bar']})
    await mailchimp_list.import_sub_activity()
    mocked_asyncio.Semaphore.assert_called_with(
        mailchimp_list.MAX_ACTIVITY_CONNECTIONS)
    async_requests_calls_args_list = [
        arg
        for args, _ in mocked_make_async_requests.call_args_list
        for arg in args]
    assert all(
        request_arg in async_requests_calls_args_list
        for request_arg in [
            mocked_sem,
            'https://bar1.api.mailchimp.com/3.0/lists/1/members/foo/activity',
            'https://bar1.api.mailchimp.com/3.0/lists/1/members/bar/activity',
        ])
    args, _ = mocked_asyncio.gather.call_args
    assert len(args) == 2
    assert_frame_equal(output_df, mailchimp_list.df)

def test_get_list_ids(mailchimp_list):
    """Tests the get_list_ids function."""
    mailchimp_list.df = pd.DataFrame({
        'id': ['foo', 'bar', 'baz'],
        'status': ['subscribed', 'unsubscribed', 'subscribed']
    })
    assert mailchimp_list.get_list_ids() == ['foo', 'baz']

def test_flatten(mailchimp_list):
    """Tests the flatten function."""
    mailchimp_list.df = pd.DataFrame({
        'id': ['foo', 'bar'],
        'status': ['subscribed', 'subscribed'],
        'timestamp_opt': ['foo', 'bar'],
        'timestamp_signup': ['foo', 'bar'],
        'recent_open': ['bar', 'baz'],
        'stats': [{
            'stats1': 'foo',
            'stats2': 'bar'
        }, {
            'stats1': 'quux',
            'stats2': 'quuz'
        }]
    })
    mailchimp_list.flatten()
    assert_frame_equal(
        mailchimp_list.df,
        pd.DataFrame({
            'id': ['foo', 'bar'],
            'status': ['subscribed', 'subscribed'],
            'timestamp_opt': ['foo', 'bar'],
            'timestamp_signup': ['foo', 'bar'],
            'recent_open': ['bar', 'baz'],
            'stats1': ['foo', 'quux'],
            'stats2': ['bar', 'quuz']
        }),
        check_like=True
    )

def test_calc_list_breakdown(mailchimp_list):
    """Tests the calc_list_breakdown function."""
    mailchimp_list.df = pd.DataFrame({
        'status': ['subscribed', 'subscribed', 'unsubscribed', 'pending']
    })
    mailchimp_list.count = 4
    mailchimp_list.calc_list_breakdown()
    assert mailchimp_list.subscribed_pct == 0.5
    assert mailchimp_list.unsubscribed_pct == 0.25
    assert mailchimp_list.cleaned_pct == 0
    assert mailchimp_list.pending_pct == 0.25

def test_calc_open_rate(mailchimp_list):
    """Tests the calc_open_rate function."""
    mailchimp_list.calc_open_rate('10')
    assert mailchimp_list.open_rate == 0.1

@pytest.mark.parametrize('campaign_count, expected_frequency', [
    ('5', 0), ('365', 1)])
def test_calc_frequency(
        mocker, mailchimp_list, campaign_count, expected_frequency):
    """Tests the calc_frequency function."""
    mocked_datetime = mocker.patch('app.lists.datetime')
    mocked_datetime.now.return_value = datetime.datetime(
        2000, 1, 1, tzinfo=datetime.timezone.utc)
    mailchimp_list.calc_frequency(
        '1999-1-1T00:00:00+00:00', campaign_count)
    assert mailchimp_list.frequency == expected_frequency

def test_calc_histogram(mailchimp_list):
    """Tests the calc_histogram function."""
    mailchimp_list.df = pd.DataFrame({
        'status': ['subscribed', 'subscribed', 'subscribed',
                   'subscribed', 'cleaned', 'subscribed'],
        'avg_open_rate': [0, 0.09, 0.56, 0.81, 0.87, 1]
    })
    mailchimp_list.calc_histogram()
    assert mailchimp_list.hist_bin_counts == (
        [2, 0, 0, 0, 0, 1, 0, 0, 1, 1])

def test_calc_high_rate_pct(mailchimp_list):
    """Tests the calc_high_open_rate_pct function."""
    mailchimp_list.df = pd.DataFrame({
        'status': ['subscribed', 'subscribed', 'subscribed',
                   'subscribed', 'cleaned', 'subscribed'],
        'avg_open_rate': [0, 0.09, 0.56, 0.81, 0.87, 1]
    })
    mailchimp_list.subscribers = 5
    mailchimp_list.calc_high_open_rate_pct()
    assert mailchimp_list.high_open_rt_pct == 0.4

def test_calc_cur_yr_stats(mailchimp_list):
    """Tests the calc_cur_yr_stats function."""
    mailchimp_list.df = pd.DataFrame({
        'recent_open': ['foo', 'bar', np.NaN, np.NaN, 'baz']
    })
    mailchimp_list.subscribers = 4
    mailchimp_list.calc_cur_yr_stats()
    assert mailchimp_list.cur_yr_inactive_pct == 0.25

def test_get_list_as_csv(mailchimp_list):
    """Tests the get_list_as_csv."""
    mailchimp_list.df = pd.DataFrame(
        {'col1': ['foo', 'bar'],
         'col2': ['bar', 'baz']})
    csv_buffer = mailchimp_list.get_list_as_csv()
    assert csv_buffer.getvalue() == 'col1,col2\nfoo,bar\nbar,baz\n'
