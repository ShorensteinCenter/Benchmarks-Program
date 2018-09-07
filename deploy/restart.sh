#!/bin/sh

cd /home/ubuntu/benchmarks-project
source benchmarks-env/bin/activate
pip install -r requirements.txt
deactivate
sudo systemctl restart app
sudo systemctl restart celeryd
sudo systemctl restart celerybeat
