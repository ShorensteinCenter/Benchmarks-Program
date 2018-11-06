import random

def test_index(client):
    """Tests the index route."""
    assert client.get('/').status_code == 200

def test_about(client):
    """Tests the about route."""
    assert client.get('/about').status_code == 200

def test_contact(client):
    """Tests the contact route."""
    assert client.get('/contact').status_code == 200

def test_terms(client):
    """Tests the terms route."""
    assert client.get('/terms').status_code == 200

def test_privacy(client):
    """Tests the privacy route."""
    assert client.get('/privacy').status_code == 200

def test_confirmation_no_params(client):
    """Tests the confirmation route with bad params."""
    assert client.get('/confirmation').status_code == 404

def test_confirmation_no_title_param(client):
    """Tests the confirmation route with no title param."""
    assert client.get('/confirmation?body=test').status_code == 404

def test_confirmation_no_body_param(client):
    """Tests the confirmation route with no body param."""
    assert client.get('/confirmation?title=test').status_code == 404

def test_confirmation(client):
    """Tests the confirmation route."""
    assert client.get('/confirmation?title=title&body=also_test').status_code == 200

def test_confirmation_title(client, random_str_list):
    """Tests that the confirmation route renders the page title."""
    title = random.choice(random_str_list)
    response = client.get('/confirmation?title={}&body=body'.format(title))
    assert title.encode() in response.data

def test_confirmation_body(client, random_str_list):
    """Tests that the confirmation route renders the page body."""
    body = random.choice(random_str_list)
    response = client.get('/confirmation?title=title&body={}'.format(body))
    assert body.encode() in response.data

def test_basic_info(client):
    pass

