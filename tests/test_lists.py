import logging
import pytest
from asynctest import CoroutineMock
from requests.exceptions import ConnectionError as ConnError
from app.lists import MailChimpImportError, MailChimpList

def test_mailchimp_import_error():
    """Tests the custom MailChimp Import Error."""
    error = MailChimpImportError('foo', 'bar')
    assert isinstance(error, MailChimpImportError)
    assert str(error) == 'foo'
    assert error.error_details == 'bar'

@pytest.mark.asyncio
async def test_enable_proxy_no_proxy(mocker, caplog):
    """Tests the enable_proxy when the NO_PROXY environment variable is
    present."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [True]
    caplog.set_level(logging.INFO)
    fake_list = MailChimpList(1, 2, 'foo-bar1', 'bar1')
    await fake_list.enable_proxy()
    assert fake_list.proxy is None
    assert ('NO_PROXY environment variable set. Not using a proxy.' in
            caplog.text)

@pytest.mark.asyncio
async def test_enable_proxy_successful(mocker, caplog):
    """Tests the enable_proxy function."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocked_current_proccess = mocker.patch('app.lists.current_process')
    mocked_current_proccess.return_value.index = 5
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.return_value.text = 'foo:bar:baz'
    caplog.set_level(logging.INFO)
    mocked_sleep = mocker.patch('app.lists.asyncio.sleep', new=CoroutineMock())
    fake_list = MailChimpList(1, 2, 'foo-bar1', 'bar1')
    await fake_list.enable_proxy()
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
    assert fake_list.proxy == 'http://bar:baz'
    assert 'Using proxy: http://bar:baz' in caplog.text
    mocked_sleep.assert_called()

@pytest.mark.asyncio
async def test_enable_proxy_unable_to_get_process_number(mocker):
    """Tests the enable_proxy function when current_process().index
    raises an AttributeError."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocked_current_proccess = mocker.patch('app.lists.current_process')
    del mocked_current_proccess.return_value.index
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.return_value.text = 'foo:bar:baz'
    mocker.patch('app.lists.asyncio.sleep', new=CoroutineMock())
    fake_list = MailChimpList(1, 2, 'foo-bar1', 'bar1')
    await fake_list.enable_proxy()
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
async def test_enable_proxy_proxy_response_error(mocker, caplog):
    """Tests the enable_proxy function when the request to the proxy provider
    returns an error."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocker.patch('app.lists.current_process')
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.return_value.text = 'ERROR:bar:baz'
    fake_list = MailChimpList(1, 2, 'foo-bar1', 'bar1')
    await fake_list.enable_proxy()
    assert fake_list.proxy is None
    assert 'Not using a proxy. Reason: baz.' in caplog.text

@pytest.mark.asyncio
async def test_enable_proxy_connection_error(mocker, caplog):
    """Tests the enable_proxy function when the request to the proxy provider
    causes a ConnectionError."""
    mocked_os = mocker.patch('app.lists.os')
    mocked_os.environ.get.side_effect = [None, 'foo']
    mocker.patch('app.lists.current_process')
    mocked_requests = mocker.patch('app.lists.requests')
    mocked_requests.get.side_effect = ConnError()
    fake_list = MailChimpList(1, 2, 'foo-bar1', 'bar1')
    await fake_list.enable_proxy()
    assert fake_list.proxy is None
    assert 'ConnectionError: proxy provider down.' in caplog.text

@pytest.mark.asyncio
async def test_make_async_request(mocker):
    """Tests the make_async_request function."""
    client_session_mock = CoroutineMock()
    client_session_mock.get.return_value.__aenter__.return_value.status = 200
    client_session_mock.get.return_value.__aenter__.return_value.text = (
        CoroutineMock(return_value='foo'))
    mocked_basic_auth = mocker.patch('app.lists.BasicAuth')
    fake_list = MailChimpList(1, 2, 'foo-bar1', 'bar1')
    async_request_response = await fake_list.make_async_request(
        'www.foo.com', 'foo', client_session_mock)
    client_session_mock.get.assert_called_with(
        'www.foo.com', params='foo',
        auth=mocked_basic_auth('shorenstein', 'foo-bar1'),
        proxy=None)
    assert async_request_response == 'foo'
