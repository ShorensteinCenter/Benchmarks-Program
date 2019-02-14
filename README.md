# Shorenstein Center Email Benchmarks

This is a tool developed by the Shorenstein Center at the Harvard Kennedy School to import MailChimp email list data, analyze it, and output the resulting metrics in an email report.

## Branches

| Branch | Tests | Code Coverage | Comments |
| ------ | ----- | ------------- | -------- |
| `devel` | [![CircleCI](https://circleci.com/gh/ShorensteinCenter/Benchmarks-Program/tree/develop.svg?style=svg)](https://circleci.com/gh/ShorensteinCenter/Benchmarks-Program/tree/develop) | [![codecov](https://codecov.io/gh/ShorensteinCenter/Benchmarks-Program/branch/develop/graph/badge.svg)](https://codecov.io/gh/ShorensteinCenter/Benchmarks-Program) | Current Work in Progress |
| `master` | [![CircleCI](https://circleci.com/gh/ShorensteinCenter/Benchmarks-Program.svg?style=svg)](https://circleci.com/gh/ShorensteinCenter/Benchmarks-Program) | [![codecov](https://codecov.io/gh/ShorensteinCenter/Benchmarks-Program/branch/master/graph/badge.svg)](https://codecov.io/gh/ShorensteinCenter/Benchmarks-Program) | Latest official release |

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

* [Python](https://www.python.org), version 3.5+ (3.6+ recommended).
* [RabbitMQ](https://www.rabbitmq.com/) or another AMQP broker.
* A relational database, e.g. [SQLite](https://www.sqlite.org) or [PostgreSQL](https://www.postgresql.org/).
* [NodeJS](https://nodejs.org). We're currently using version 11.2, but any recent version should work. (We use [NVM](https://github.com/creationix/nvm) to manage Node versions.) 
* [Amazon SES](https://aws.amazon.com/ses/) (optional, see below).

### Local Development

##### Create a new virtual environment

    virtualenv venv
    source venv/bin/activate

##### Install Python dependencies

    pip install -r requirements.txt

##### Set environment variables

* `SECRET_KEY` - Flask secret key.
* `CELERY_BROKER_URI` - The URI of the Celery broker. Default `'amqp://guest:guest@localhost:5672/'` (a broker running locally on port `5672`).
* `SQLALCHEMY_DATABASE_URI` - The URI of the database. Default is a `sqlite` database named `app.db` located at the application root.
* `SERVER_NAME` - the URL for the app. Default `127.0.0.1:5000` (suitable for running locally). Note that the URLs for assets sent via email (images, etc.) are generated using Flask's `url_for()` function. If `SERVER_NAME` is not externally accessible these assets will not send succesfully.
* `NO_PROXY` - We use proxies to distribute our MailChimp requests across IP addresses. Set this variable to `True` in order to disable proxying, or modify the `enable_proxy` method in `app/lists.py` according to your proxy configuration.
* `NO_EMAIL` - If set, suppresses sending of email reports (as well as error emails, etc.).

If `NO_EMAIL` is not set, Amazon SES is required along with the following variables:

* `AWS_ACCESS_KEY_ID` - AWS Access Key ID for the API.
* `AWS_SECRET_ACCESS_KEY` - AWS Secret Access Key for the API.
* `SES_REGION_NAME` - AWS Simple Email Service region. Default `us-west-2`.
* `SES_DEFAULT_EMAIL_SOURCE` - The default email address to send from. This email needs to be verified by SES and active outside the SES sandbox.
* `ADMIN_EMAIL` - Email address to send error emails to. Optional.
* `SES_CONFIGURATION_SET` - SES Configuration Set for tracking opens/clicks/etc. Optional.

The following variables are only required to run integration tests:

* `TESTING_API_KEY` - MailChimp API key to use in integration tests.
* `TESTING_LIST_ID` - MailChimp list ID to run integration tests against.

##### Upgrade the database

    export FLASK_APP=app.py
    flask db upgrade

##### Install Node dependencies

    npm install

You may need to add the installed binaries to your system path (or install with the `-g` flag), as the application expects to find certain executables (such as `orca`).

##### Compile front-end

    npm run gulp

##### Run the application

    flask run

##### Run Celery

    celery worker -A app.celery --loglevel=INFO

Finally, open a web browser and navigate to the `SERVER_NAME` URI.

## Testing

Run unit and integration tests with `pytest`:

    python -m pytest tests/unit
    python -m pytest tests/integration

To generate a coverage report as well:

    python -m pytest --cov=app --cov-report term-missing tests/unit

## Linting

Lint the backend with `pylint`:

    pylint app

Lint the frontend:

    npm run lint

Python and Javascript rules are defined in `pylintrc` and `.eslintrc`, respectively.

## Deployment

This app is environment-agnostic. We deployed it on Ubuntu using `gunicorn` and `nginx`, and daemonized `Celery` and `Celery Beat`. Here are a few pointers on what we did.

A sample init script for gunicorn:

    [Unit]
    Description=Gunicorn instance to serve app
    After=network.target

    [Service]
    User=app_user
    Group=www-data
    WorkingDirectory=/path/to/app
    Environment="PATH=/path/to/app/venv/bin"
    ExecStart=/path/to/app/venv/bin/gunicorn --workers 5 --bind unix:email-benchmarks.sock -m 007 app:app

    [Install]
    WantedBy=multi-user.target

A sample init script for nginx:

    server {
        listen 80;
        server_name SERVER_NAME;

        location / {
            include proxy_params;
            proxy_pass http://unix:/path/to/app/email-benchmarks.sock;
        }
    }

Sample init scripts for `Celery` can be found in the [Celery repo](https://github.com/celery/celery/tree/master/extra/generic-init.d/).

Setting up [Orca](https://github.com/plotly/orca) (required for exporting visualizations from Plotly) can be tricky on headless machines. We got it to work by installing the standalone binaries and additional dependencies (such as `google-chrome-stable`) as per the `readme`, then using Xvfb with the `-a` flag, i.e. `xvfb-run -a ...`. Additionally, restarting a daemonized Celery will create a new xvfb instance rather than re-using the one that is already running. We added the following function to our Celery init script, which kills running xvfb processes:

    kill_xvfb () {
        local xvfb_pids=`ps aux | grep tmp/xvfb-run | grep -v grep | awk '{print $2}'`
        if [ "$xvfb_pids" != "" ]; then
            echo "Killing the following xvfb processes: $xvfb_pids"
            sudo kill $xvfb_pids
        else
            echo "No xvfb processes to kill"
        fi
    }    

## Authors

* **William Hakim** - [William Hakim](https://github.com/williamhakim10)

## Acknowledgements

This project is generously supported by the [Knight Foundation](https://knightfoundation.org/).

We use [Browserstack](https://www.browserstack.com/) to help ensure our projects work across platforms and devices.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
