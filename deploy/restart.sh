#!/bin/sh

cd /home/ubuntu/benchmarks-project
source benchmarks-env/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart app
sudo /etc/init.d/celeryd restart
sudo /etc/init.d/celerybeat restart
