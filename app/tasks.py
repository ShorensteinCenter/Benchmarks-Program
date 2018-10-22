"""This module contains Celery tasks and functions associated with them."""
import os
import json
import random
from collections import OrderedDict
import requests
from sqlalchemy.sql.functions import func
from celery.utils.log import get_task_logger
from app import celery, db
from app.emails import send_email
from app.lists import MailChimpList, MailChimpImportError, do_async_import
from app.models import ListStats, AppUser
from app.charts import BarChart, Histogram, render_png
from app.dbops import associate_user_with_list

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

    # Create a list object
    list_stats = ListStats(
        list_id=list_data['list_id'],
        list_name=list_data['list_name'],
        api_key=list_data['key'],
        data_center=list_data['data_center'],
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
        store_aggregates=list_data['store_aggregates'],
        monthly_updates=list_data['monthly_updates'],
        org_id=org_id)

    # If the user gave their permission, store the object in the database
    if list_data['monthly_updates'] or list_data['store_aggregates']:
        list_stats = db.session.merge(list_stats)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

    return list_stats

def send_report(stats, list_id, list_name, user_email_or_emails):
    """Generates charts using Pygal and emails them to the user.

    Args:
        stats: a dictionary containing analysis results for a list.
        list_id: the list's unique MailChimp id.
        list_name: the list's name.
        user_email_or_emails: a list of emails to send the report to.
    """

    # Generate averages from the database
    # Only include lists where we have permission
    avg_stats = db.session.query(
        func.avg(ListStats.subscribers),
        func.avg(ListStats.open_rate),
        func.avg(ListStats.subscribed_pct),
        func.avg(ListStats.unsubscribed_pct),
        func.avg(ListStats.cleaned_pct),
        func.avg(ListStats.pending_pct),
        func.avg(ListStats.high_open_rt_pct),
        func.avg(ListStats.cur_yr_inactive_pct)).filter_by(
            store_aggregates=True).first()

    # Make sure we have no 'None' values
    avg_stats = [avg if avg else 0 for avg in avg_stats]

    # Generate charts
    # Using OrderedDict (for now) as Pygal occasionally seems to break with
    # The Python 3.5 dictionary standard which preserves order by default
    # Export them as pngs to /charts
    list_size_chart = BarChart(
        'Chart A: List Size vs. Database Average (Mean)',
        OrderedDict(
            [('Your List', [stats['subscribers']]),
             ('Average (Mean)', [avg_stats[0]])]),
        percentage=False)
    render_png(list_size_chart, list_id + '_size')

    list_breakdown_chart = BarChart(
        'Chart B: List Composition vs. Database Average (Mean)',
        OrderedDict(
            [('Subscribed %', [stats['subscribed_pct'], avg_stats[2]]),
             ('Unsubscribed %', [stats['unsubscribed_pct'], avg_stats[3]]),
             ('Cleaned %', [stats['cleaned_pct'], avg_stats[4]]),
             ('Pending %', [stats['pending_pct'], avg_stats[5]])]),
        x_labels=('Your List', 'Average (Mean)'))
    render_png(list_breakdown_chart, list_id + '_breakdown')

    open_rate_chart = BarChart(
        'Chart C: List Open Rate vs. Database Average (Mean)',
        OrderedDict(
            [('Your List', [stats['open_rate']]),
             ('Average (Mean)', [avg_stats[1]])]))
    render_png(open_rate_chart, list_id + '_open_rate')

    open_rate_hist_chart = Histogram(
        'Chart D: Distribution of User Unique Open Rates',
        OrderedDict(
            [('Your List', stats['hist_bin_counts'])]))
    render_png(open_rate_hist_chart, list_id + '_open_rate_histogram')

    high_open_rt_pct_chart = BarChart(
        'Chart E: Percentage of Subscribers with User Unique Open Rate '
        '>80% vs. Database Average (Mean)',
        OrderedDict(
            [('Your List', [stats['high_open_rt_pct']]),
             ('Average (Mean)', [avg_stats[6]])]))
    render_png(high_open_rt_pct_chart, list_id + '_high_open_rt')

    cur_yr_member_pct_chart = BarChart(
        'Chart F: Percentage of Subscribers who did not Open in last 365 '
        'Days vs. Database Average (Mean)',
        OrderedDict(
            [('Your List', [stats['cur_yr_inactive_pct']]),
             ('Average (Mean)', [avg_stats[7]])]))
    render_png(cur_yr_member_pct_chart, list_id + '_cur_yr_inactive_pct')

    # Send charts as an email report
    send_email('Your Email Benchmarking Report is Ready!',
               user_email_or_emails,
               'report-email.html',
               {'title': 'We\'ve analyzed the {} list!'.format(list_name),
                'list_id': list_id},
               configuration_set_name=(
                   os.environ.get('SES_CONFIGURATION_SET') or None))

def extract_stats(list_object):
    """Extracts a stats dictionary from a list object from the database."""
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

    First checks if the list stats are cached, i.e. already in the
    database. If not, calls import_analyze_store_list() to generate
    them. Then checks if the user is already associated with the list,
    if not, create the relationship. Finally, generates a benchmarking
    report with the stats.

    Args:
        user_data: a dictionary containing information about the user.
        list_data: a dictionary containing information about the list.
        org_id: the id of the organization associated with the list.
    """

    # Try to pull the list stats from database
    # Otherwise generate them
    list_object = (ListStats.query.filter_by(
        list_id=list_data['list_id']).first() or
                   import_analyze_store_list(
                       list_data, org_id, user_data['email']))

    # Associate the list with the user who requested the analysis
    # If that user requested monthly updates
    if list_data['monthly_updates']:
        associate_user_with_list(user_data['user_id'], list_object)

    stats = extract_stats(list_object)
    send_report(stats, list_data['list_id'],
                list_data['list_name'], [user_data['email']])

@celery.task
def update_stored_data():
    """Celery task which goes through the database
    and updates calculations using the most recent data.

    This task is called by Celery Beat, see the schedule in config.py.
    """

    # Get the logger
    logger = get_task_logger(__name__)

    # Grab what we have in the database
    list_objects = ListStats.query.with_entities(
        ListStats.list_id, ListStats.list_name, ListStats.org_id,
        ListStats.api_key, ListStats.data_center,
        ListStats.store_aggregates, ListStats.monthly_updates).all()

    if not list_objects:
        logger.info('No lists to update!')
        return

    # Placeholder for lists which failed during the update process
    failed_updates = []

    # Update 1/30th of the lists in the database (such that every list
    # is updated about once per month, on average).
    lists_to_update = random.sample(
        list_objects, len(list_objects) // 31 if len(list_objects) // 31 else 1)

    # Update each list's calculations in sequence
    for list_to_update in lists_to_update:

        logger.info('Updating list %s!', list_to_update.list_id)

        # Pull information about the list from the API
        # This may have changed since we originally pulled the list data
        request_uri = ('https://{}.api.mailchimp.com/3.0/lists/{}'.format(
            list_to_update.data_center, list_to_update.list_id))
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
            auth=('shorenstein', list_to_update.api_key))
        response_body = response.json()
        response_stats = response_body['stats']
        count = (response_stats['member_count'] +
                 response_stats['unsubscribe_count'] +
                 response_stats['cleaned_count'])

        # Create a dictionary of list data
        list_data = {'list_id': list_to_update.list_id,
                     'list_name': list_to_update.list_name,
                     'key': list_to_update.api_key,
                     'data_center': list_to_update.data_center,
                     'monthly_updates': list_to_update.monthly_updates,
                     'store_aggregates': list_to_update.store_aggregates,
                     'total_count': count,
                     'open_rate': response_stats['open_rate'],
                     'date_created': response_body['date_created'],
                     'campaign_count': response_stats['campaign_count']}

        # Then re-run the calculations and update the database
        try:
            import_analyze_store_list(list_data, list_to_update.org_id)
        except MailChimpImportError:
            logger.error('Error updating list %s.', list_to_update.list_id)
            failed_updates.append(list_to_update.list_id)

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
    monthly_report_lists = ListStats.query.filter_by(
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

        # Extract stats from the list object
        stats = extract_stats(monthly_report_list)
        send_report(stats, monthly_report_list.list_id,
                    monthly_report_list.list_name,
                    users_to_email)
