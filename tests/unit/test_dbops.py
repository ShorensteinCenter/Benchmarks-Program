import pytest
from sqlalchemy.exc import IntegrityError
from app.dbops import update_user, store_user, store_org, associate_user_with_list

def test_update_user(mocker):
    """Tests the update_user function."""
    mocked_user_obj = mocker.patch('app.dbops.AppUser')
    mocked_user = mocked_user_obj.query.filter_by.return_value.first.return_value
    mocked_user.orgs = []
    mocked_db = mocker.patch('app.dbops.db')
    user = update_user({'name': 'foo', 'email': 'foo@bar.com'}, 'bar')
    mocked_user_obj.query.filter_by.assert_called_with(email='foo@bar.com')
    assert mocked_user.name == 'foo'
    assert mocked_user.orgs == ['bar']
    mocked_db.session.commit.assert_called()
    assert user == mocked_user

def test_update_user_db_exception(mocker):
    """Tests the update_user function when the database throws an exception."""
    mocker.patch('app.dbops.AppUser')
    mocked_db = mocker.patch('app.dbops.db')
    mocked_db.session.commit.side_effect = Exception()
    with pytest.raises(Exception):
        update_user({'name': 'foo', 'email': 'foo@bar.com'}, 'bar')
    mocked_db.session.rollback.assert_called()

def test_store_user(mocker):
    """Tests the store_user function."""
    mocked_user_obj = mocker.patch('app.dbops.AppUser')
    mocked_user = mocked_user_obj.return_value
    mocked_db = mocker.patch('app.dbops.db')
    user = store_user('foo', 'foo@bar.com', 'bar', 'baz')
    mocked_user_obj.assert_called_with(
        name='foo', email='foo@bar.com', email_hash='bar', approved=False,
        orgs=['baz'])
    mocked_db.session.add.assert_called_with(mocked_user)
    mocked_db.session.commit.assert_called()
    assert user == mocked_user

def test_store_user_integrityerror(mocker):
    """Tests the store_user function. Database commit raises an IntegrityError."""
    mocker.patch('app.dbops.AppUser')
    mocked_db = mocker.patch('app.dbops.db')
    mocked_db.session.commit.side_effect = IntegrityError('foo', 'bar', 'baz')
    mocked_update_user = mocker.patch('app.dbops.update_user')
    store_user('foo', 'foo@bar.com', 'bar', 'baz')
    mocked_db.session.rollback.assert_called()
    mocked_update_user.assert_called_with(
        {'name': 'foo', 'email': 'foo@bar.com', 'email_hash': 'bar'},
        'baz')

def test_store_user_othererror(mocker):
    """Tests the store user function Database commit raises a differerent error."""
    mocker.patch('app.dbops.AppUser')
    mocked_db = mocker.patch('app.dbops.db')
    mocked_db.session.commit.side_effect = Exception()
    with pytest.raises(Exception):
        store_user('foo', 'foo@bar.com', 'bar', 'baz')
    mocked_db.session.rollback.assert_called()

def test_store_org(mocker):
    """Tests the store_org function."""
    mocked_org_obj = mocker.patch('app.dbops.Organization')
    mocked_org = mocked_org_obj.return_value
    mocked_db = mocker.patch('app.dbops.db')
    organization = store_org({'foo': 'bar'})
    mocked_org_obj.assert_called_with(foo='bar')
    mocked_db.session.add.assert_called_with(mocked_org)
    mocked_db.session.commit.assert_called()
    assert organization == mocked_org

def test_store_org_db_exception(mocker):
    """Tests the store_org function when the database throws an exception."""
    mocker.patch('app.dbops.Organization')
    mocked_db = mocker.patch('app.dbops.db')
    mocked_db.session.commit.side_effect = Exception()
    with pytest.raises(Exception):
        store_org({'foo': 'bar'})
    mocked_db.session.rollback.assert_called()

def test_associate_user_with_list(mocker):
    """Tests the associate_user_with_list function."""
    mocked_user_obj = mocker.patch('app.dbops.AppUser')
    mocked_user = mocked_user_obj.query.filter_by.return_value.first.return_value
    mocked_user.lists = []
    mocked_db = mocker.patch('app.dbops.db')
    associate_user_with_list('foo', 'bar')
    mocked_user_obj.query.filter_by.assert_called_with(id='foo')
    assert mocked_user.lists == ['bar']
    mocked_db.session.commit.assert_called()

def test_associate_user_with_list_db_exception(mocker):
    """Tests the associate_user_with_List function when the database throws
    an exception."""
    mocker.patch('app.dbops.AppUser')
    mocked_db = mocker.patch('app.dbops.db')
    mocked_db.session.commit.side_effect = Exception()
    with pytest.raises(Exception):
        associate_user_with_list('foo', 'bar')
    mocked_db.session.rollback.assert_called()
