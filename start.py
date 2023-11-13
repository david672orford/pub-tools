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
from app.utils.clean_logs import CleanlogWSGIRequestHandler

debug_mode = listen_all = False
for arg in sys.argv[1:]:
	match arg:
		case "--debug":
			debug_mode = True
		case "--debug-requests":
			from http.client import HTTPConnection
			HTTPConnection.debuglevel = 1
		case "--listen-all":
			listen_all = True

logging.basicConfig(
	level=logging.DEBUG if debug_mode else logging.INFO,
	format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

app = create_app()
run_simple("0.0.0.0" if listen_all else "127.0.0.1", 5000, app, request_handler=CleanlogWSGIRequestHandler, threaded=True)
