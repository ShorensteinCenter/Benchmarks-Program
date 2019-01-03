from werkzeug import ImmutableMultiDict
from app import db
from app.models import Organization, AppUser

def test_store_new_user(client):
    """End-to-end test of submitting the /validate-basic-info route with a
    new user and an existing organization."""
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
    db.session.commit()
    userform = ImmutableMultiDict([
        ('name', 'foo'), ('email', 'foo@bar.com'), ('news_org', 'foo bar')])
    response = client.post('/validate-basic-info', data=userform)
    user = AppUser.query.filter_by(email='foo@bar.com').first()
    assert user.name == 'Foo'
    assert len(user.orgs) == 1
    assert existing_org in user.orgs
    assert response.get_json()['user'] == 'other'

def test_store_existing_user(client, caplog):
    """End-to-end test of submitting the /validate-basic-info route with an
    existing user and an existing organization."""
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
    userform = ImmutableMultiDict([
        ('name', 'bar'), ('email', 'foo@bar.com'), ('news_org', 'foo bar')])
    response = client.post('/validate-basic-info', data=userform)
    user = AppUser.query.filter_by(email='foo@bar.com').first()
    assert user.name == 'Bar'
    assert len(user.orgs) == 1
    assert user.orgs[0].name == 'Foo Bar'
    assert response.get_json()['user'] == 'approved'
    assert ('Suppressing an email with the following params: '
            'Sender: testing@testing.com. Recipients: [\'foo@bar.com\']. '
            'Subject: You\'re all set to access our benchmarks!'
            in caplog.text)

def test_store_organization(client):
    """End-to-end tests of submitting the /validate-org-infon route with a new
    user and new organization."""
    orgform = ImmutableMultiDict([
        ('financial_classification', 'For-Profit'),
        ('coverage_scope', 'City'),
        ('coverage_focus', 'Investigative'),
        ('platform', 'Digital Only'),
        ('employee_range', '5 or fewer'),
        ('budget', '$500k-$2m'),
        ('news_revenue_hub', True),
        ('other_affiliation', True),
        ('other_affiliation_name', 'Baz')])
    with client as c:
        with c.session_transaction() as sess:
            sess['user_name'] = 'Foo'
            sess['email'] = 'foo@bar.com'
            sess['email_hash'] = 'f3ada405ce890b6f8204094deb12d8a8'
            sess['org'] = 'Bar'
        response = c.post('/validate-org-info', data=orgform)
        assert response.get_json()['user'] == 'other'
    user = AppUser.query.filter_by(email='foo@bar.com').first()
    assert user.name == 'Foo'
    assert len(user.orgs) == 1
    org = user.orgs[0]
    assert org.name == 'Bar'
    assert org.budget == '$500k-$2m'
    assert org.affiliations == '["News Revenue Hub", "Baz"]'
