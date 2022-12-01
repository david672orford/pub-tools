#! /usr/bin/python3
#
# This script runs Pub-Tools as a standalone web server.
#
# To start it:
#
#   ./start.py
#
# Then browser to:
#
#   http://127.0.0.1:5000
#

import sys
import logging
from werkzeug.serving import run_simple
from app import create_app

debug_mode = listen_all = False
for arg in sys.argv[1:]:
	if arg == "--debug":
		debug_mode = True
	elif arg == "--listen-all":
		listen_all = True

logging.basicConfig(
	level=logging.DEBUG if debug_mode else logging.INFO,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

app = create_app()
run_simple("0.0.0.0" if listen_all else "127.0.0.1", 5000, app, threaded=True)
