#!/bin/sh

sudo systemctl restart app
sudo /etc/init.d/celeryd restart
sudo /etc/init.d/celerybeat restart
