sudo kill $(ps aux | grep /tmp/xvfb-run | awk '{print $2}' | head -n -1)
sudo systemctl restart celeryd
