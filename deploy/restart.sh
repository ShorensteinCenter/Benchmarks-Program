#!/bin/sh

sudo systemctl restart app
sudo /etc/init.d/celeryd restart 1>/dev/null 
sudo /etc/init.d/celerybeat restart 1>/dev/null
