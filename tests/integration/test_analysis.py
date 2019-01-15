import os
import glob
import json
import requests
from app import db
from app.models import AppUser, Organization, EmailList

def test_analysis(client, caplog):
    """End-to-end test of analyzing a list."""
    existing_org = Organization(
        name='Foo Bar',
        financial_classification='',
        coverage_scope='',
        coverage_focus='',
        platform='',
        employee_range='',
        budget='',
        affiliations='')
    db.session.add(existing_org)
    existing_user = AppUser(
        name='Foo',
        email='foo@bar.com',
        email_hash='f3ada405ce890b6f8204094deb12d8a8',
        approved=True,
        orgs=[existing_org])
    db.session.add(existing_user)
    db.session.commit()
    existing_org_id = existing_org.id
    existing_user_id = existing_user.id
    list_id = os.environ.get('TESTING_LIST_ID')
    api_key = os.environ.get('TESTING_API_KEY')
    data_center = api_key.rsplit('-', 1)[1]
    chart_files = glob.glob('app/static/charts/*.png')
    for file in chart_files:
        if list_id in file:
            os.remove(file)
    request_uri = 'https://{}.api.mailchimp.com/3.0/lists/{}'.format(
        data_center, list_id)
    params = (
        ('fields', 'name,'
                   'stats.member_count,'
                   'stats.unsubscribe_count,'
                   'stats.cleaned_count,'
                   'stats.open_rate,'
                   'date_created,'
                   'stats.campaign_count'),
    )
    response = requests.get(request_uri, params=params,
                            auth=('email-benchmarks-testing', api_key))
    data = response.json()
    request_data = {
        'list_id': list_id,
        'list_name': data['name'],
        'total_count': (data['stats']['member_count'] +
                        data['stats']['unsubscribe_count'] +
                        data['stats']['cleaned_count']),
        'open_rate': data['stats']['open_rate'],
        'date_created': data['date_created'],
        'campaign_count': data['stats']['campaign_count']
    }
    with client as c:
        with c.session_transaction() as sess:
            sess['user_id'] = existing_user_id
            sess['email'] = 'foo@bar.com'
            sess['key'] = api_key
            sess['data_center'] = data_center
            sess['monthly_updates'] = True
            sess['store_aggregates'] = True
            sess['org_id'] = existing_org_id
        response = c.post('/analyze-list', data=json.dumps(request_data),
                          content_type='application/json')
        assert response.status == '200 OK'
    chart_files = glob.glob('app/static/charts/*.png')
    assert any(list_id + '_size_' in file for file in chart_files)
    assert any(list_id + '_breakdown_' in file for file in chart_files)
    assert any(list_id + '_open_rate_' in file for file in chart_files)
    assert any(list_id + '_open_rate_histogram_' in file for file in chart_files)
    assert any(list_id + '_high_open_rt_pct_' in file for file in chart_files)
    assert any(list_id + '_cur_yr_inactive_pct_' in file for file in chart_files)
    assert ('Suppressing an email with the following params: '
            'Sender: testing@testing.com. Recipients: [\'foo@bar.com\']. '
            'Subject: Your Email Benchmarking Report is Ready!'
            in caplog.text)
    email_list = EmailList.query.filter_by(list_id=list_id).first()
    assert email_list
    assert email_list.org.id == existing_org_id
    assert email_list.monthly_update_users[0].id == existing_user_id
    assert email_list.analyses[0]
    assert email_list.analyses[0].open_rate == data['stats']['open_rate']
