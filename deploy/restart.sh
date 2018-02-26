#!/bin/sh

sudo systemctl restart app
sudo /etc/init.d/celeryd restart
sudo chown celery:celery /home/ubuntu/benchmarks-project/app.db