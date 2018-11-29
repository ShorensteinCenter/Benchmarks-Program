#!/bin/sh

sudo systemctl restart app
sh restart-celery.sh
sudo systemctl restart celerybeat
