"""This module contains database operations, e.g. insert, update, etc."""
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import AppUser, Organization

def update_user(user_info, org):
    """Updates a user in the database.

    Args:
        user_info: a dictionary of user information.
        org: see store_user().
    """
    user = AppUser.query.filter_by(email=user_info['email']).first()
    try:
        user.name = user_info['name']
        user.orgs.append(org)
        db.session.commit()
    except:
        db.session.rollback()
        raise

def store_user(name, email, email_hash, org):
    """Inserts a new user into the database.

    Args:
        name: name of the user.
        email: user's email address.
        email_hash: md5-hash of the email address.
        org: SQLAlchemy Organization object representing the
            news organization the user belongs to.
    """
    user_info = {'name': name,
                 'email': email,
                 'email_hash': email_hash}

    # The new user isn't approved for access by default
    user = AppUser(**user_info, approved=False, orgs=[org])

    # Do a bootleg upsert (due to lack of ORM support)
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        update_user(user_info, org)
    except:
        db.session.rollback()
        raise

def store_org(org_info):
    """Inserts a new orgaization into the database.

    Args:
        org_info: a dictionary containing information about the organization.
            Each element corresponds to an Organization attribute defined in
            the database model.

    Returns:
        The inserted Organization object.
    """
    organization = Organization(**org_info)
    db.session.add(organization)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise
    return organization

def associate_user_with_list(user_id, list_object):
    """Associates a user in the database with a list object.

    Args:
        user_id: the unique id of the user to be updated.
        list_object: the list_stats object to associate.
    """
    user = AppUser.query.filter_by(id=user_id).first()
    user.lists.append(list_object)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise
