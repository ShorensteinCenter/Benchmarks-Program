"""This module handles the data science operations on email lists."""
import io
import os
import json
import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from billiard import current_process # pylint: disable=no-name-in-module
import requests
from requests.exceptions import ConnectionError as ConnError
import pandas as pd
from pandas.io.json import json_normalize
import numpy as np
from aiohttp import ClientSession, BasicAuth
import iso8601
from celery.utils.log import get_task_logger

def do_async_import(coroutine):
    """Generic wrapper function to run async imports.

    Args:
        coroutine: the coroutine to be run asynchronously
    """
    loop = asyncio.get_event_loop()
    future = asyncio.ensure_future(coroutine)
    loop.run_until_complete(future)

class MailChimpImportError(ConnectionError):
    """A custom exception raised when async imports fail."""
    def __init__(self, message, error_details):
        super().__init__(message)
        self.error_details = error_details

class MailChimpList(): # pylint: disable=too-many-instance-attributes
    """A class representing a MailChimp list."""

    # The max size of a request to the MailChimp API
    # This is for direct requests to the members endpoint
    CHUNK_SIZE = 5000

    # The number of simultaneous connections we'll make to the API
    # The API limit is 10
    # But we want to make sure we don't interrupt other tasks
    MAX_CONNECTIONS = 4

    # The number of simultanous connections for the activity import phase
    # This number is lower than MAX_CONNECTIONS
    # Otherwise MailChimp will flag as too many requests
    # (Each request takes very little time to complete)
    MAX_ACTIVITY_CONNECTIONS = 2

    # The http status codes we'd like to retry in case of a connection issue
    HTTP_STATUS_CODES_TO_RETRY = [429, 504]

    # The number of times to retry an http request in case of a timeout
    MAX_RETRIES = 3

    # The base backoff time in seconds
    BACKOFF_INTERVAL = 5

    # The approximate amount of seconds it takes to cold boot a proxy
    PROXY_BOOT_TIME = 30

    def __init__(self, id, count, api_key, data_center): # pylint: disable=redefined-builtin
        """Initializes a MailCimp list.

        Args:
            id: the list's unique MailChimp id.
            count: the total size of the list, including subscribed,
                unsubscribed, pending, and cleaned.
            api_key: a MailChimp api key associated with the list.
            data_center: the data center where the list is stored,
                e.g. 'us2'. Used in MailChimp api calls.

        Other class variables:
            proxy: the proxy to use for making MailChimp API requests.
            df: the pandas dataframe to perform calculations on.
            frequency: how often a campaign is sent on average.
            subscribers: the number of active subscribers.
            open_rate: the list's open rate.
            hist_bin_counts: a list containing the percentage of subscribers
                with open rates in each decile.
            subscribed_pct: the percentage of list members who are subscribers.
            unsubscribed_pct: the percentage of list  members who unsubscibed.
            cleaned_pct: the percentage of list members whose addresses have
                been cleaned.
            pending_pct: the percentage of list members who are pending, i.e.
                haven't completed double opt-in.
            high_open_rt_pct: the percentage of list members who open more
                than 80% of emails.
            cur_yr_active_pct: the percentage of list members who registered
                an 'open' event in the past 365 days.
        """
        self.id = id # pylint: disable=invalid-name
        self.count = int(count)
        self.api_key = api_key
        self.data_center = data_center
        self.logger = get_task_logger(__name__)

        self.proxy = None
        self.df = None # pylint: disable=invalid-name
        self.frequency = None
        self.subscribers = None
        self.open_rate = None
        self.hist_bin_counts = None
        self.subscribed_pct = None
        self.unsubscribed_pct = None
        self.cleaned_pct = None
        self.pending_pct = None
        self.high_open_rt_pct = None
        self.cur_yr_inactive_pct = None

    async def enable_proxy(self):
        """Enables a proxy server.

        Requests are proxied through US Proxies to prevent MailChimp
        blocks. This is an accepted technique among integrators and
        does not violate MailChimp's Terms of Service.
        """

        # Don't use a proxy if environment variable is set, e.g. in development
        if os.environ.get('NO_PROXY'):
            self.logger.info(
                'NO_PROXY environment variable set. Not using a proxy.')
            return

        # Get the worker number for this Celery worker
        # We want each worker to control its corresponding proxy process
        # Note that workers are zero-indexed, proxy procceses are not
        process = current_process()

        # Fall back to proxy #1 if we can't ascertain the worker index
        # e.g. anyone hacking with this app on windows
        try:
            proxy_process_number = str(process.index + 1)
        except AttributeError:
            proxy_process_number = '1'

        # Use the US Proxies API to get the proxy info
        proxy_request_uri = 'http://us-proxies.com/api.php'
        proxy_params = (
            ('api', ''),
            ('uid', '9557'),
            ('pwd', os.environ.get('PROXY_AUTH_PWD')),
            ('cmd', 'rotate'),
            ('process', proxy_process_number),
        )

        try:
            proxy_response = requests.get(proxy_request_uri,
                                          params=proxy_params)
            proxy_response_vars = proxy_response.text.split(':')

            # Set the proxy for requests from this worker
            # Keep as None (i.e, use the server's IP)
            # Only if we have an issue with the proxy provider
            if proxy_response_vars[0] != 'ERROR':
                self.proxy = ('http://{}:{}'.format(
                    proxy_response_vars[1], proxy_response_vars[2]))

        # If proxy provider is unreachable, don't use a proxy
        except ConnError:
            proxy_response_vars = None

        # Allow some time for the proxy server to boot up
        # We don't need to wait if we're not using a proxy
        if self.proxy:
            self.logger.info('Using proxy: %s', self.proxy)
            await asyncio.sleep(self.PROXY_BOOT_TIME)
        else:
            self.logger.warning('Not using a proxy. Reason: %s.',
                                proxy_response_vars[2] if
                                proxy_response_vars else
                                'ConnectionError: proxy provider down.')

    async def make_async_request(self, url, params, session, retry=0):
        """Makes an async request using aiohttp.

        Makes a get request.
        If successful, returns the response text future.
        If the request times out, or returns a status code
        that we want to retry, recursively retry the request
        up to MAX_RETRIES times using exponential backoff.

        Args:
            url: The url to make the request to.
            params: The HTTP GET parameters.
            session: The aiohttp ClientSession to make requests with.
            retry: The number of previous attempts at this individual
                request.

        Returns:
            An asyncio future, which, when awaited,
            contains the request response.

        Throws:
            MailChimpImportError: The request keeps returning a bad HTTP status
                code and/or timing out with no response.
        """
        try:

            # Make the async request with aiohttp
            async with session.get(url, params=params,
                                   auth=BasicAuth('shorenstein',
                                                  self.api_key),
                                   proxy=self.proxy) as response:

                # If we got a 200 OK, return the request response
                if response.status == 200:
                    return await response.text()

                # Always log the bad response
                self.logger.warning('Received invalid response code: '
                                    '%s. URL: %s. API key: %s. '
                                    'Response: %s.', response.status,
                                    url, self.api_key,
                                    response.reason)

                # Retry if we got an error
                # And we haven't already retried a few times
                if (response.status in self.HTTP_STATUS_CODES_TO_RETRY
                        and retry < self.MAX_RETRIES):

                    # Increment retry count, log, sleep and then retry
                    retry += 1
                    self.logger.info('Retrying (%s)', retry)
                    await asyncio.sleep(self.BACKOFF_INTERVAL ** retry)
                    return await self.make_async_request(
                        url, params, session, retry)

                # Prepare some details for the user
                error_details = OrderedDict([
                    ('err_desc', 'An error occurred when '
                                 'trying to import your data '
                                 'from MailChimp.'),
                    ('mailchimp_err_code', response.status),
                    ('mailchimp_url', url),
                    ('api_key', self.api_key),
                    ('mailchimp_err_reason', response.reason)])

                # Log the error and raise an exception
                self.logger.exception('Invalid response code from MailChimp')
                raise MailChimpImportError(
                    'Invalid response code from MailChimp',
                    error_details)

        # Catch proxy problems as well as potential asyncio timeouts/disconnects
        except Exception as e: # pylint: disable=invalid-name

            exception_type = type(e).__name__

            # If we're just catching the exception raised above
            # don't need to do anything else
            if exception_type == 'MailChimpImportError':
                raise

            # Otherwise, log what happened as appropriate
            if exception_type == 'ClientHttpProxyError':
                self.logger.warning('Failed to connect to proxy! Proxy: %s',
                                    self.proxy)

            elif exception_type == 'ServerDisconnectedError':
                self.logger.warning('Server disconnected! URL: %s. API key: '
                                    '%s.', url, self.api_key)

            elif exception_type == 'TimeoutError':
                self.logger.warning('Asyncio request timed out! URL: %s. '
                                    'API key: %s.', url, self.api_key)

            else:
                self.logger.warning('An unforseen error type occurred. '
                                    'Error type: %s. URL: %s. API Key: %s.',
                                    exception_type, url, self.api_key)

            # Retry if we haven't already retried a few times
            if retry < self.MAX_RETRIES:

                # Increment retry count, log, sleep, and then retry
                retry += 1
                self.logger.info('Retrying (%s)', retry)
                await asyncio.sleep(self.BACKOFF_INTERVAL ** retry)
                return await self.make_async_request(
                    url, params, session, retry)

            # Prepare some details for the user
            error_details = OrderedDict([
                ('err_desc', 'An error occurred when '
                             'trying to import your data from MailChimp.'),
                ('application_exception', exception_type),
                ('mailchimp_url', url),
                ('api_key', self.api_key)])

            # Log the error and raise an exception
            self.logger.exception('Error in async request to MailChimp (%s)',
                                  exception_type)

            raise MailChimpImportError(
                'Error in async request to MailChimp ({})'.format(
                    exception_type),
                error_details)

    async def make_async_requests(self, sem, url, params, session):
        """Makes a number of async requests using a semaphore.

        Args:
            sem: A semaphore to limit the number of concurrent async
                requests.
            url: See make_async_request().
            params: See make_async_request().
            session: See make_async_request().

        Returns:
            An asyncio future resolved into a dictionary containing
                request results.
        """
        async with sem:
            res = await self.make_async_request(url, params, session)
            return json.loads(res)

    async def import_list_members(self):
        """Requests basic information about MailChimp list members in chunks.

        This includes the member status, member stats, etc.
        Requests are made asynchronously (up to CHUNK_SIZE members
        per requests) using aiohttp. This speeds up the process
        significantly and prevents timeouts.
        After the requests have completed, parses the results and turns
        them into a pandas dataframe.
        """

        # Enable a proxy
        await self.enable_proxy()

        # MailChimp API endpoint for requests
        request_uri = ('https://{}.api.mailchimp.com/3.0/lists/{}/'
                       'members'.format(self.data_center, self.id))

        # List of async tasks to do
        tasks = []

        # Placeholder for async responses
        responses = None

        # Semaphore to limit max simultaneous connections to MailChimp API
        sem = asyncio.Semaphore(self.MAX_CONNECTIONS)

        # The total number of chunks, i.e. requests to make to MailChimp
        # If list is smaller than CHUNK_SIZE, this is 1 request
        number_of_chunks = (1 if self.count < self.CHUNK_SIZE
                            else self.count // self.CHUNK_SIZE + 1)

        # Make requests with a single session
        async with ClientSession() as session:
            for chunk_num in range(number_of_chunks):

                # Calculate the number of members in this request
                chunk = (str(self.count % self.CHUNK_SIZE
                             if chunk_num == number_of_chunks - 1
                             else self.CHUNK_SIZE))

                # Calculate where to begin request from
                offset = str(chunk_num * self.CHUNK_SIZE)

                params = (
                    ('fields', 'members.status,'
                               'members.timestamp_opt,'
                               'members.timestamp_signup,'
                               'members.stats,members.id'),
                    ('count', chunk),
                    ('offset', offset),
                )

                # Add a new import task to the queue for each chunk
                task = asyncio.ensure_future(
                    self.make_async_requests(
                        sem, request_uri, params, session))
                tasks.append(task)

            # Await completion of all requests and gather results
            responses = await asyncio.gather(*tasks)

        # Close the session
        await session.close()

        # Flatten the responses into a single list of dicts
        list_data = [response
                     for response_dict in responses
                     for v in response_dict.values()
                     for response in v]

        # Create a pandas dataframe to store the results
        self.df = pd.DataFrame(list_data) # pylint: disable=invalid-name

    async def import_sub_activity(self): # pylint: disable=too-many-locals
        """Requests each subscriber's recent activity.

        First, gets a list of subscribers.
        Then makes the requests one-by-one using aiohttp (MailChimp's API is
        very inefficient and you cannot request multiple subscribers' activity
        at the same time).
        After the requests have completed, parses the results, turns them into
        a pandas dataframe, and merges this dataframe with the members
        dataframe created by import_list_members().
        """
        params = (
            ('fields', 'activity.action,activity.timestamp,email_id'),
            ('exclude_fields', 'total_items,_links')
        )

        request_uri = ('https://{}.api.mailchimp.com/3.0/lists/{}/members/'
                       '{}/activity'.format(self.data_center, self.id, '{}'))

        # List of async tasks to do
        tasks = []

        # Placeholder for async responses
        responses = None

        # Semaphore to limit max simultaneous connections to MailChimp API
        sem = asyncio.Semaphore(self.MAX_ACTIVITY_CONNECTIONS)

        # Get a list of unique subscriber ids
        subscriber_list = self.get_list_ids()

        # Store the number of subscribers for later
        self.subscribers = len(subscriber_list)

        # Create a session with which to make requests
        async with ClientSession() as session:
            for subscriber_id in subscriber_list:

                # Format the request string
                request_string = request_uri.format(subscriber_id)

                # Add a new import task to the queue for each list subscriber
                task = asyncio.ensure_future(
                    self.make_async_requests(
                        sem, request_string, params, session))
                tasks.append(task)

            # Await completion of all requests and gather results
            responses = await asyncio.gather(*tasks)

        # Close the session
        await session.close()

        # Calculate timestamp for one year ago
        now = datetime.now(timezone.utc)
        one_year_ago = now - timedelta(days=365)

        # Flatten responses
        # Filter out activity older than one year
        activities = [{**{'id': response['email_id']},
                       **{'recent_open': d['timestamp']
                          for d in response['activity']
                          if d['action'] == 'open' and
                          iso8601.parse_date(d['timestamp']) > one_year_ago}}
                      for response in responses]

        # Convert results to a dataframe
        subscriber_activities = pd.DataFrame(activities)

        # Merge dataframes if any subscribers have recently opened
        # Else add an empty recent_open column to dataframe
        # This allows us to assume that a 'recent open' column exists
        if 'recent_open' in subscriber_activities:
            self.df = pd.merge(self.df,
                               subscriber_activities,
                               on='id',
                               how='left')
        else:
            self.df['recent_open'] = np.NaN

    def get_list_ids(self):
        """Returns a list of md5-hashed email ids for subscribers only."""
        return self.df[self.df['status'] == 'subscribed']['id'].tolist()

    def flatten(self):
        """Removes nested jsons from the dataframe."""

        # Extract member stats from nested json
        # Then store them in a flattened dataframe
        stats = json_normalize(self.df['stats'].tolist())

        # Merge the dataframes
        self.df = (self.df[['status', 'timestamp_opt', 'timestamp_signup',
                            'id', 'recent_open']].join(stats))

    def calc_list_breakdown(self):
        """Calculates the list breakdown."""
        statuses = self.df.status.unique()
        self.subscribed_pct = (
            0 if 'subscribed' not in statuses
            else self.df.status.value_counts()['subscribed'] /
            self.count)
        self.unsubscribed_pct = (
            0 if 'unsubscribed' not in statuses
            else self.df.status.value_counts()['unsubscribed'] /
            self.count)
        self.cleaned_pct = (
            0 if 'cleaned' not in statuses
            else self.df.status.value_counts()['cleaned'] /
            self.count)
        self.pending_pct = (
            0 if 'pending' not in statuses
            else self.df.status.value_counts()['pending'] /
            self.count)

    def calc_open_rate(self, open_rate):
        """Calculates the open rate as a decimal."""
        self.open_rate = float(open_rate) / 100

    def calc_frequency(self, date_created, campaign_count):
        """Calculates the average number of days per campaign sent. Automatically
        zero if fewer than 10 campaigns have been sent total."""
        campaign_count = int(campaign_count)
        if campaign_count < 10:
            self.frequency = 0
        else:
            now = datetime.now(timezone.utc)
            created = iso8601.parse_date(date_created)
            list_age = now - created
            self.frequency = list_age.days / campaign_count

    def calc_histogram(self):
        """Calculates the distribution for subscriber open rate."""
        bin_boundaries = np.linspace(0, 1, num=11)
        bins = (pd.cut(
            self.df.loc[self.df['status'] == 'subscribed', 'avg_open_rate'],
            bin_boundaries, include_lowest=True))
        self.hist_bin_counts = (pd.value_counts(bins, sort=False).tolist())

    def calc_high_open_rate_pct(self):
        """Calcuates the percentage of subscribers who open >80% of emails."""

        # Sum the number of rows where average open rate exceeds 0.8
        # And the member is a subscriber
        # Then divide by the total number of rows
        self.high_open_rt_pct = (
            sum(x > 0.8 for x in self.df[self.df['status'] == 'subscribed']
                ['avg_open_rate']) / self.subscribers)

    def calc_cur_yr_stats(self):
        """Calculates metrics related to activity
        that occured in the previous year."""

        # Total number of subsribers without an open within the last year
        cur_yr_inactive_subs = (self.subscribers -
                                int(self.df['recent_open'].count()))

        # Percent of such subscribers
        self.cur_yr_inactive_pct = cur_yr_inactive_subs / self.subscribers

    def get_list_as_csv(self):
        """Returns a string buffer containing a CSV of the list data."""
        csv_buffer = io.StringIO()
        self.df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)
        return csv_buffer
