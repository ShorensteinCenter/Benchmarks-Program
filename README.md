# Shorenstein Center Email Benchmarks

This is a tool developed by the Shorenstein Center at the Harvard Kennedy School to import MailChimp email list data, analyze it, and output the resulting metrics in an email report.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Prerequisites

You will need ```Python >=3.6```, ```RabbitMQ```, and ```Celery```. ```Celery Beat``` is optional but recommended for production use. You will also need a relational database to connect to the application.

### Installing

Create a new virtual environment:

```
virtualenv email-benchmarks
source email-benchmarks/bin/activate
```

Install requirements:

```
pip install -r requirements.txt
```

Modify ```config.py```, paying particular attention to the ```SQLALCHEMY_DATABASE_URI```, ```SERVER_NAME```, and all of the Flask-Mail configuration variables. Note that while ```SERVER_NAME``` can be excluded (or set to localhost), Flask-Mail will fail to generate a url adapter and the application will crash when it attempts to send an email.

We use proxies to distribute our MailChimp requests across IP addresses. You will need to modify the ```import_list_async``` function in ```app/lists.py``` or remove the proxy functionality. 

Upgrade the database:

```
export FLASK_APP=app.py
flask db migrate
flask db upgrade
```

Run the application:

```
flask run
```

Separately, run the Celery worker:

```
celery worker -A app.celery --loglevel=INFO
```

Finally, open a web browser and navigate to the ```SERVER_NAME``` URI.

## Compiling SCSS and JS with Gulp

You will need ```node.js``` and ```npm``` installed. Then run:

```
npm install
```

To build and watch the frontend source files, run:

```
gulp
```

The ```.eslintrc``` file defines Javascript rules.

## Deployment

This app is environment-agnostic. We deployed it on Ubuntu using ```gunicorn``` and ```nginx```, and daemonized ```Celery``` and ```Celery Beat```. Here are a few pointers on what we did.

A sample init script for gunicorn:

```
[Unit]
Description=Gunicorn instance to serve app
After=network.target

[Service]
User=app_user
Group=www-data
WorkingDirectory=/path/to/app
Environment="PATH=/path/to/app/email-benchmarks/bin"
ExecStart=/path/to/app/email-benchmarks/bin/gunicorn --workers 5 --bind unix:email-benchmarks.sock -m 007 app:app

[Install]
WantedBy=multi-user.target
```

A sample init script for nginx:

```
server {
    listen 80;
    server_name SERVER_NAME;

    location / {
        include proxy_params;
        proxy_pass http://unix:/path/to/app/email-benchmarks.sock;
    }
}
```

Sample init scripts for Celery can be found in the [Celery repo](https://github.com/celery/celery/tree/3.1/extra/generic-init.d/).

## Authors

* **William Hakim** - [William Hakim](https://github.com/williamhakim10)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
