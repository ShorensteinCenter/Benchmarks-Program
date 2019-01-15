"""This module contains Celery tasks and functions associated with them."""
import os
import json
import time
from datetime import datetime, timedelta, timezone
import requests
import numpy as np
from sqlalchemy import desc
from sqlalchemy.sql.functions import func
from celery.utils.log import get_task_logger
from app import celery, db
from app.emails import send_email
from app.lists import MailChimpList, MailChimpImportError, do_async_import
from app.models import EmailList, ListStats
from app.dbops import associate_user_with_list
from app.visualizations import (
    draw_bar, draw_stacked_horizontal_bar, draw_histogram, draw_donuts)

@celery.task
def send_activated_email(user_email, user_email_hash):
    """Sends an email telling a user that they've been authorized.

    Args:
        user_email: the email address of the user.
        user_email_hash: the hash of the user's email address.
    """
    send_email('You\'re all set to access our benchmarks!',
               [user_email],
               'activated-email.html',
               {'title': 'You\'re all set to access our benchmarks!',
                'email_hash': user_email_hash})

def import_analyze_store_list(list_data, org_id, user_email=None):
    """Imports a MailChimp list, performs calculations, and stores results.

    Args:
        list_data: see init_list_analysis().
        org_id: the unique id of the organization associated with the list.
        user_email: the user's email address. Only passed when the user
            requested the analysis (as opposed to Celery Beat).

    Returns:
        A dictionary containing analysis results for the list.

    Throws:
        MailChimpImportError: an error resulting from a
            MailChimp API problem.
    """

    # Create a new list instance and import member data/activity
    mailing_list = MailChimpList(
        list_data['list_id'], list_data['total_count'], list_data['key'],
        list_data['data_center'])

    try:

        # Import basic list data
        do_async_import(mailing_list.import_list_members())

        # Import the subscriber activity as well, and merge
        do_async_import(mailing_list.import_sub_activity())

    except MailChimpImportError as e: # pylint: disable=invalid-name
        if user_email:
            send_email(
                'We Couldn\'t Process Your Email Benchmarking Report',
                [user_email, os.environ.get('ADMIN_EMAIL') or None],
                'error-email.html',
                {'title': 'Looks like something went wrong ☹',
                 'error_details': e.error_details})
        raise

    # Remove nested jsons from the dataframe
    mailing_list.flatten()

    # Do the data science shit
    mailing_list.calc_list_breakdown()
    mailing_list.calc_open_rate(list_data['open_rate'])
    mailing_list.calc_frequency(list_data['date_created'],
                                list_data['campaign_count'])
    mailing_list.calc_histogram()
    mailing_list.calc_high_open_rate_pct()
    mailing_list.calc_cur_yr_stats()

    # Create a set of stats
    list_stats = ListStats(
        frequency=mailing_list.frequency,
        subscribers=mailing_list.subscribers,
        open_rate=mailing_list.open_rate,
        hist_bin_counts=json.dumps(mailing_list.hist_bin_counts),
        subscribed_pct=mailing_list.subscribed_pct,
        unsubscribed_pct=mailing_list.unsubscribed_pct,
        cleaned_pct=mailing_list.cleaned_pct,
        pending_pct=mailing_list.pending_pct,
        high_open_rt_pct=mailing_list.high_open_rt_pct,
        cur_yr_inactive_pct=mailing_list.cur_yr_inactive_pct,
        list_id=list_data['list_id'])

    # If the user gave their permission, store the stats in the database
    if list_data['monthly_updates'] or list_data['store_aggregates']:

        # Create a list object to go with the set of stats
        email_list = EmailList(
            list_id=list_data['list_id'],
            list_name=list_data['list_name'],
            api_key=list_data['key'],
            data_center=list_data['data_center'],
            store_aggregates=list_data['store_aggregates'],
            monthly_updates=list_data['monthly_updates'],
            org_id=org_id)
        email_list = db.session.merge(email_list)

        db.session.add(list_stats)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

    return list_stats

def send_report(stats, list_id, list_name, user_email_or_emails):
    """Generates charts using Plotly and emails them to the user.

    Args:
        stats: a dictionary containing analysis results for a list.
        list_id: the list's unique MailChimp id.
        list_name: the list's name.
        user_email_or_emails: a list of emails to send the report to.
    """

    # This subquery generates the most recent stats
    # For each unique list_id in the database
    # Where store_aggregates is True
    subquery = ListStats.query.filter(
        ListStats.list.has(store_aggregates=True)).order_by('list_id', desc(
            'analysis_timestamp')).distinct(ListStats.list_id).subquery()

    # Generate aggregates within the subquery
    agg_stats = db.session.query(
        func.avg(subquery.columns.subscribers),
        func.avg(subquery.columns.subscribed_pct),
        func.avg(subquery.columns.unsubscribed_pct),
        func.avg(subquery.columns.cleaned_pct),
        func.avg(subquery.columns.pending_pct),
        func.avg(subquery.columns.open_rate),
        func.avg(subquery.columns.high_open_rt_pct),
        func.avg(subquery.columns.cur_yr_inactive_pct)).first()

    # Make sure we have no 'None' values
    agg_stats = [agg if agg else 0 for agg in agg_stats]

    # Convert subscribers average to an integer
    agg_stats[0] = int(agg_stats[0])

    # Generate epoch time (to get around image caching in webmail)
    epoch_time = str(int(time.time()))

    # Generate charts
    draw_bar(
        ['Your List', 'Dataset Average'],
        [stats['subscribers'], agg_stats[0]],
        'Chart A: List Size',
        list_id + '_size_' + epoch_time)

    draw_stacked_horizontal_bar(
        ['Dataset Average', 'Your List'],
        [('Subscribed %', [agg_stats[1], stats['subscribed_pct']]),
         ('Unsubscribed %', [agg_stats[2], stats['unsubscribed_pct']]),
         ('Cleaned %', [agg_stats[3], stats['cleaned_pct']]),
         ('Pending %', [agg_stats[4], stats['pending_pct']])],
        'Chart B: List Composition',
        list_id + '_breakdown_' + epoch_time)

    draw_bar(
        ['Your List', 'Dataset Average'],
        [stats['open_rate'], agg_stats[5]],
        'Chart C: List Open Rate',
        list_id + '_open_rate_' + epoch_time,
        percentage_values=True)

    histogram_legend_uri = ('https://s3-us-west-2.amazonaws.com/email-'
                            'benchmarking-imgs/open_rate_histogram_legend.png')

    draw_histogram(
        {'title': 'Open Rate by Decile', 'vals': np.linspace(.05, .95, num=10)},
        {'title': 'Subscribers', 'vals': stats['hist_bin_counts']},
        'Chart D: Distribution of Subscribers by Open Rate',
        histogram_legend_uri,
        list_id + '_open_rate_histogram_' + epoch_time)

    draw_donuts(
        ['Open Rate >80%', 'Open Rate <=80%'],
        [('Your List',
          [stats['high_open_rt_pct'], 1 - stats['high_open_rt_pct']]),
         ('Dataset Average', [agg_stats[6], 1 - agg_stats[6]])],
        'Chart E: Percentage of Subscribers with User Unique Open Rate >80%',
        list_id + '_high_open_rt_pct_' + epoch_time)

    draw_donuts(
        ['Inactive in Past 365 Days', 'Active in Past 365 Days'],
        [('Your List',
          [stats['cur_yr_inactive_pct'], 1 - stats['cur_yr_inactive_pct']]),
         ('Dataset Average', [agg_stats[7], 1 - agg_stats[7]])],
        'Chart F: Percentage of Subscribers who did not Open '
        'in last 365 Days',
        list_id + '_cur_yr_inactive_pct_' + epoch_time)

    # Send charts as an email report
    send_email('Your Email Benchmarking Report is Ready!',
               user_email_or_emails,
               'report-email.html',
               {'title': 'We\'ve analyzed the {} list!'.format(list_name),
                'list_id': list_id,
                'epoch_time': epoch_time},
               configuration_set_name=(
                   os.environ.get('SES_CONFIGURATION_SET') or None))

def extract_stats(list_object):
    """Extracts a stats dictionary from a SQLAlchemy ListStats object."""
    stats = {'subscribers': list_object.subscribers,
             'open_rate': list_object.open_rate,
             'hist_bin_counts': json.loads(list_object.hist_bin_counts),
             'subscribed_pct': list_object.subscribed_pct,
             'unsubscribed_pct': list_object.unsubscribed_pct,
             'cleaned_pct': list_object.cleaned_pct,
             'pending_pct': list_object.pending_pct,
             'high_open_rt_pct': list_object.high_open_rt_pct,
             'cur_yr_inactive_pct': list_object.cur_yr_inactive_pct}
    return stats

@celery.task
def init_list_analysis(user_data, list_data, org_id):
    """Celery task wrapper for each stage of analyzing a list.

    First checks if there is a recently cached analysis, i.e. already in the
    database. If not, calls import_analyze_store_list() to generate
    the ListStats and an associated EmailList. Next updates the user's
    privacy options (e.g. store_aggregates, monthly_updates) if the list was
    cached. Then checks if the user selected monthly updates, if so,
    create the relationship. Finally, generates a benchmarking
    report with the stats.

    Args:
        user_data: a dictionary containing information about the user.
        list_data: a dictionary containing information about the list.
        org_id: the id of the organization associated with the list.
    """

    # Try to pull the most recent ListStats from the database
    # Otherwise generate them
    most_recent_analysis = (ListStats.query.filter_by(
        list_id=list_data['list_id']).order_by(desc(
            'analysis_timestamp')).first() or import_analyze_store_list(
                list_data, org_id, user_data['email']))

    # If the user chose to store their data, there will be an associated
    # EmailList object
    list_object = EmailList.query.filter_by(
        list_id=list_data['list_id']).first()

    if list_object:

        # Update the privacy options if they differ from previous selection
        if (list_object.monthly_updates != list_data['monthly_updates']
                or list_object.store_aggregates != list_data['store_aggregates']):
            list_object.monthly_updates = list_data['monthly_updates']
            list_object.store_aggregates = list_data['store_aggregates']
            list_object = db.session.merge(list_object)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                raise

        # Associate the list with the user who requested the analysis
        # If that user requested monthly updates
        if list_data['monthly_updates']:
            associate_user_with_list(user_data['user_id'], list_object)

    # Convert the ListStats object to an easier-to-use dictionary
    stats = extract_stats(most_recent_analysis)
    send_report(stats, list_data['list_id'],
                list_data['list_name'], [user_data['email']])

@celery.task
def update_stored_data():
    """Celery task which goes through the database
    and generates a new set of calculations for each list older than 30 days.

    This task is called by Celery Beat, see the schedule in config.py.
    """
    logger = get_task_logger(__name__)

    # Grab the most recent analyses in the database
    list_analyses = ListStats.query.order_by(
        'list_id', desc('analysis_timestamp')).distinct(
            ListStats.list_id).all()

    if not list_analyses:
        logger.warning('No lists in the database!')
        return

    # Create a list of analyses which are more than 30 days old
    now = datetime.now(timezone.utc)
    one_month_ago = now - timedelta(days=30)
    analyses_to_update = [
        analysis for analysis in list_analyses
        if (analysis.analysis_timestamp.replace(
            tzinfo=timezone.utc)) < one_month_ago]

    if not analyses_to_update:
        logger.info('No old lists to update!')
        return

    # Placeholder for lists which failed during the update process
    failed_updates = []

    # Update each list's calculations in sequence
    for analysis in analyses_to_update:

        logger.info('Updating list %s!', analysis.list_id)

        # Get the list object associated with the analysis
        associated_list_object = analysis.list

        # Pull information about the list from the API
        # This may have changed since we originally pulled the list data
        request_uri = ('https://{}.api.mailchimp.com/3.0/lists/{}'.format(
            associated_list_object.data_center,
            associated_list_object.list_id))
        params = (
            ('fields', 'stats.member_count,'
                       'stats.unsubscribe_count,'
                       'stats.cleaned_count,'
                       'stats.open_rate,'
                       'date_created,'
                       'stats.campaign_count'),
        )
        response = requests.get(
            request_uri, params=params,
            auth=('shorenstein', associated_list_object.api_key))
        response_body = response.json()
        response_stats = response_body['stats']
        count = (response_stats['member_count'] +
                 response_stats['unsubscribe_count'] +
                 response_stats['cleaned_count'])

        # Create a dictionary of list data
        list_data = {'list_id': analysis.list_id,
                     'list_name': associated_list_object.list_name,
                     'key': associated_list_object.api_key,
                     'data_center': associated_list_object.data_center,
                     'monthly_updates': associated_list_object.monthly_updates,
                     'store_aggregates': associated_list_object.store_aggregates,
                     'total_count': count,
                     'open_rate': response_stats['open_rate'],
                     'date_created': response_body['date_created'],
                     'campaign_count': response_stats['campaign_count']}

        # Then re-run the calculations and update the database
        try:
            import_analyze_store_list(list_data, associated_list_object.org_id)
        except MailChimpImportError:
            logger.error('Error updating list %s.', analysis.list_id)
            failed_updates.append(analysis.list_id)

    # If any updates failed, raise an exception to send an error email
    if failed_updates:
        raise MailChimpImportError(
            'Some lists failed to update: {}'.format(failed_updates),
            failed_updates)

@celery.task
def send_monthly_reports():
    """Celery task which sends monthly benchmarking reports
    to each user who requested one.

    This task is called by Celery Beat, see the schedule in config.py.
    """
    logger = get_task_logger(__name__)

    # Grab info from the database
    monthly_report_lists = EmailList.query.filter_by(
        monthly_updates=True).all()

    # Send an email report for each list
    for monthly_report_list in monthly_report_lists:

        # Extract the users associated with each list
        # Who requested a monthly update email
        users_to_email = [user.email for user
                          in monthly_report_list.monthly_update_users]
        for email in users_to_email:
            logger.info('Emailing %s an updated report. List: %s (%s).',
                        email,
                        monthly_report_list.list_name,
                        monthly_report_list.list_id)

        # Get the most recent analysis for the list
        stats_object = ListStats.query.filter_by(
            list_id=monthly_report_list.list_id).order_by(
                desc('analysis_timestamp')).first()

        # Extract stats from the list object
        stats = extract_stats(stats_object)
        send_report(stats, monthly_report_list.list_id,
                    monthly_report_list.list_name,
                    users_to_email)
