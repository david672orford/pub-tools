#! /usr/bin/env python3
#
# Install OBS Studio
#
#    $ sudo add-apt-repository ppa:obsproject/obs-studio
#    $ sudo apt install obs-studio
#
# Install the Video For Linux Loopback Device
#
#    $ sudo apt install v4l2loopback-dkms
#
# Install OBS Websocket
#
#    $ wget https://github.com/Palakis/obs-websocket/releases/download/4.9.1/obs-websocket_4.9.1-1_amd64.deb
#    $ sudo dpkg -i obs-websocket_4.9.1-1_amd64.deb
#    $ sudo apt install -f
#    $ pip3 install obs-websocket-py
#
# Start JW-Meeting
#
#    $ ./start.py
#

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from werkzeug.serving import run_simple
import logging
from app import app, obs_control

# Modules have the logging level set to INFO except when we are debugging
# them. Let the DEBUG messages through here.
logging.basicConfig(level=logging.DEBUG)

with open("/proc/modules") as modules:
	for line in modules:
		if line.startswith("v4l2loopback "):
			break
	else:
		sys.stderr.write("Module v4l2loopback is not loaded.\n")
		sys.exit(1)

if not obs_control.connect():
	sys.stderr.write("Cannot connect to OBS Studio.\n")
	sys.exit(1)

run_simple('0.0.0.0', 5000, app, threaded=True)
