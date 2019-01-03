import pytest
from app.emails import send_email

@pytest.mark.parametrize('sender, config_set_arg, config_set, tags', [
    (None, None, '', []),
    ('foo@bar.com', 'foo', 'foo', [{'Name': 'foo', 'Value': 'foo'}])
])
def test_send_email(test_app, mocker, sender, config_set_arg,
                    config_set, tags):
    """Tests the send_email function."""
    mocked_boto3_client = mocker.patch('app.emails.boto3.client')
    mocked_boto3_client_instance = mocked_boto3_client.return_value
    mocked_render_template = mocker.patch('app.emails.render_template')
    mocked_template_html = mocked_render_template.return_value
    test_app.config['NO_EMAIL'] = False
    with test_app.app_context():
        test_app.config['SES_REGION_NAME'] = 'foo'
        test_app.config['AWS_ACCESS_KEY_ID'] = 'bar'
        test_app.config['AWS_SECRET_ACCESS_KEY'] = 'baz'
        test_app.config['SES_DEFAULT_EMAIL_SOURCE'] = 'foo@bar.com'
        send_email('foo', ['bar'], 'foo.html', {'baz': 'qux'},
                   sender=sender,
                   configuration_set_name=config_set_arg)
        mocked_boto3_client.assert_called_with(
            'ses',
            region_name='foo',
            aws_access_key_id='bar',
            aws_secret_access_key='baz')
        mocked_render_template.assert_called_with('foo.html', baz='qux')
        mocked_boto3_client_instance.send_email.assert_called_with(
            Source='foo@bar.com',
            Destination={'ToAddresses': ['bar']},
            Message={
                'Subject': {'Data': 'foo'},
                'Body': {
                    'Html': {'Data': mocked_template_html}
                }
            },
            ConfigurationSetName=config_set,
            Tags=tags
        )

def test_send_error_email_or_email_disabled(test_app, mocker, caplog):
    """Tests the send_email function for an error email or if NO_EMAIL is set."""
    mocked_boto3_client = mocker.patch('app.emails.boto3.client')
    mocker.patch('app.emails.render_template')
    test_app.config['NO_EMAIL'] = True
    with test_app.app_context():
        test_app.config['SES_REGION_NAME'] = 'foo'
        test_app.config['AWS_ACCESS_KEY_ID'] = 'bar'
        test_app.config['AWS_SECRET_ACCESS_KEY'] = 'baz'
        test_app.config['SES_DEFAULT_EMAIL_SOURCE'] = 'foo@bar.com'
        send_email('foo', ['bar'], 'foo.html', {})
        log_text = ('NO_EMAIL environment variable set. '
                    'Suppressing an email with the following params: '
                    'Sender: {}. Recipients: {}. Subject: {}.'.format(
                        'foo@bar.com', ['bar'], 'foo'))
        assert log_text in caplog.text
        mocked_boto3_client.return_value.send_email.assert_not_called()
