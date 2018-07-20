"""This module contains Celery tasks and functions associated with them."""
import json
from collections import OrderedDict
import requests
from flask import render_template
from flask_mail import Message
from sqlalchemy.sql.functions import func
from sqlalchemy.exc import IntegrityError
from app import app, celery, db, mail
from app.lists import MailChimpList, do_async_import
from app.models import ListStats, AppUser
from app.charts import BarChart, Histogram, render_png

def update_user(user_info):
    """Updates information about an app user.

    Args:
        user_info: a dictionary of user information (see store_user()).
    """
    AppUser.query.filter_by(email=user_info['email']).update(user_info)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise

@celery.task
def store_user(news_org, contact_person, email, email_hash, newsletters):
    """Celery task which stores information about whoever is
    currently using the app.

    Args:
        news_org: news organization the user belongs to.
        contact_person: name of the person representing the organization.
        email: news organization or contact person's email address.
        email_hash: md5-hash of the email address.
        newsletters: string containing email newsletter names.
    """
    user_info = {'news_org': news_org,
                 'contact_person': contact_person,
                 'email': email,
                 'email_hash': email_hash,
                 'newsletters': newsletters}

    # The new user isn't approved for access by default
    user = AppUser(**user_info, approved=False)

    # Do a bootleg upsert (due to lack of ORM support)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        update_user(user_info)
    except:
        db.session.rollback()
        raise

@celery.task
def send_activated_email(user_id):
    """Sends an email telling a user that they've been authorized.

    Args:
        user_id: the user's unique id.
    """

    # Request the user's email and email hash from the database
    result = AppUser.query.with_entities(
        AppUser.email, AppUser.email_hash).filter_by(id=user_id).first()

    # Send an email with a unique link
    with app.app_context():
        msg = Message('You\'re all set to access our benchmarks!',
                      sender='shorensteintesting@gmail.com',
                      recipients=[result.email],
                      html=render_template('activated-email.html',
                                           title='You\'re all set to '
                                           'access our benchmarks!',
                                           email_hash=result.email_hash))
        mail.send(msg)

def import_analyze_store_list(list_id, list_name, count, open_rate,
                              user_session):
    """Imports a MailChimp list, performs calculations, and stores results.

    Args:
        See init_list_analysis().

    Returns:
        A dictionary containing analysis results for the list.
    """

    # Create a new list instance and import member data/activity
    mailing_list = MailChimpList(
        list_id, open_rate, count, user_session['key'],
        user_session['data_center'], user_session['email'])

    # Import basic list data
    do_async_import(mailing_list.import_list_members())

    # Import the subscriber activity as well, and merge
    do_async_import(mailing_list.import_sub_activity())

    # Remove nested jsons from the dataframe
    mailing_list.flatten()

    # Do the data science shit
    mailing_list.calc_list_breakdown()
    mailing_list.calc_open_rate()
    mailing_list.calc_histogram()
    mailing_list.calc_high_open_rate_pct()
    mailing_list.calc_cur_yr_stats()

    # Get list stats
    stats = mailing_list.get_list_stats()

    # Store the stats in database if we have permission
    # Serialize the histogram data so it can be stored as string
    if user_session['monthly_updates'] or user_session['store_aggregates']:
        list_stats = ListStats(
            list_id=list_id,
            list_name=list_name,
            user_id=user_session['id'],
            api_key=user_session['key'],
            data_center=user_session['data_center'],
            subscribers=stats['subscribers'],
            open_rate=stats['open_rate'],
            hist_bin_counts=json.dumps(stats['hist_bin_counts']),
            subscribed_pct=stats['subscribed_pct'],
            unsubscribed_pct=stats['unsubscribed_pct'],
            cleaned_pct=stats['cleaned_pct'],
            pending_pct=stats['pending_pct'],
            high_open_rt_pct=stats['high_open_rt_pct'],
            cur_yr_inactive_pct=stats['cur_yr_inactive_pct'],
            store_aggregates=user_session['store_aggregates'],
            monthly_updates=user_session['monthly_updates'])
        db.session.merge(list_stats)
        try:
            db.session.commit()
        except:
            db.session.rollback()
            raise

    return stats

def send_report(stats, list_id, list_name, user_email):
    """Generates charts using Pygal and emails them to the user.

    Args:
        stats: a dictionary containing analysis results for a list.
        list_id: the list's unique MailChimp id.
        list_name: the list's name.
        user_email: the list user's email address.
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
    with app.app_context():
        msg = Message('Your Email Benchmarking Report is Ready!',
                      sender='shorensteintesting@gmail.com',
                      recipients=[user_email],
                      html=render_template('report-email.html',
                                           title='We\'ve analyzed the '
                                           '{} List!'.format(list_name),
                                           list_id=list_id))
        mail.send(msg)

# Pull in list data, perform calculations, store results
# Send benchmarking report to user
@celery.task
def init_list_analysis(user_session, list_id, list_name, count,
                       open_rate):
    """Celery task wrapper for each stage of analyzing a list.

    First checks if the list stats are cached, i.e. already in the
    database. If not, calls import_analyze_store_list() to generate
    them. Then generates a benchmarking report with those stats.

    Args:
        user_session: a dictionary containing details about the user.
        list_id: the list's unique MailChimp id.
        list_name: the list's name.
        count: the total size of the list, including subscribed,
            unsubscribed, pending, and cleaned.
        open_rate: the list's open rate.
    """

    # Try to pull the list stats from database
    existing_list = (ListStats.query.filter_by(list_id=list_id).first())

    # Placeholder for list stats
    stats = None

    if existing_list is None:

        stats = import_analyze_store_list(
            list_id, list_name, count, open_rate, user_session)

    else:

        # Get list stats from database results
        # Deserialize the histogram data
        stats = {'subscribers': existing_list.subscribers,
                 'open_rate': existing_list.open_rate,
                 'hist_bin_counts': json.loads(existing_list.hist_bin_counts),
                 'subscribed_pct': existing_list.subscribed_pct,
                 'unsubscribed_pct': existing_list.unsubscribed_pct,
                 'cleaned_pct': existing_list.cleaned_pct,
                 'pending_pct': existing_list.pending_pct,
                 'high_open_rt_pct': existing_list.high_open_rt_pct,
                 'cur_yr_inactive_pct': existing_list.cur_yr_inactive_pct}

    send_report(stats, list_id, list_name, user_session['email'])

@celery.task
def update_stored_data():
    """Celery task which goes through the database
    and updates all calculations using the most recent data.

    This task is called by Celery Beat.
    """

    # Grab what we have in the database
    lists_stats = ListStats.query.with_entities(
        ListStats.list_id, ListStats.list_name, ListStats.user_id,
        ListStats.api_key, ListStats.data_center,
        ListStats.store_aggregates, ListStats.monthly_updates,
        AppUser.email).join(AppUser).all()

    # Update each list's calculations in sequence
    for list_stats in lists_stats:

        # First repull the number of list members
        # And the list overall open rate
        # This may have changed since we originally pulled the list data
        request_uri = ('https://{}.api.mailchimp.com/3.0/lists/{}'.format(
            list_stats.data_center, list_stats.list_id))
        params = (
            ('fields', 'stats.member_count,'
                       'stats.unsubscribe_count,'
                       'stats.cleaned_count,'
                       'stats.open_rate'),
        )
        response = requests.get(
            request_uri, params=params,
            auth=('shorenstein', list_stats.api_key))
        response_stats = response.json().get('stats')
        count = (response_stats['member_count'] +
                 response_stats['unsubscribe_count'] +
                 response_stats['cleaned_count'])
        open_rate = response_stats['open_rate']


        # Create a 'simulated session', i.e.
        # A dict similar to what the session would look like
        # If the user were active
        simulated_session = {'id': list_stats.user_id,
                             'email': list_stats.email,
                             'key': list_stats.api_key,
                             'data_center': list_stats.data_center,
                             'store_aggregates': list_stats.store_aggregates,
                             'monthly_updates': list_stats.monthly_updates}

        # Then re-run the calculations and update the database
        stats = import_analyze_store_list(
            list_stats.list_id, list_stats.list_name, count,
            open_rate, simulated_session)

        # If the user asked for monthly updates, send new report
        if list_stats.monthly_updates:
            send_report(
                stats, list_stats.list_id, list_stats.list_name,
                simulated_session['email'])
