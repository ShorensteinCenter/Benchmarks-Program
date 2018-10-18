"""This module contains functions associated with sending email."""
import boto3
from flask import render_template
from app import app

def send_email(subject, recipients, template_name, template_context,
               sender=None, configuration_set_name=None):
    """Sends an email using Amazon SES according to the args provided.

    Args:
        subject: the email subject line.
        recipients: list of recipient email addresses.
        template_name: the name of the template to render as the html body.
        template_context: the context to be passed to the html template.
        sender: sender's email address. Optional.
    """
    ses = boto3.client(
        'ses',
        region_name=app.config['SES_REGION_NAME'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )
    if not sender:
        sender = app.config['SES_DEFAULT_EMAIL_SOURCE']

    # Set up tracking for sends, opens, clicks, etc.
    # if an SES configuration set for tracking such metrics was included
    message_tags = []
    if configuration_set_name:
        message_tags.append({'Name': configuration_set_name,
                             'Value': configuration_set_name})

    with app.app_context():
        html = render_template(template_name, **template_context)
        ses.send_email(
            Source=sender,
            Destination={'ToAddresses': recipients},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html}
                }
            },
            ConfigurationSetName=configuration_set_name or '',
            Tags=message_tags
        )
