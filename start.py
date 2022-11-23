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

debug_mode = (len(sys.argv) >= 2 and sys.argv[1] == '--debug')

logging.basicConfig(
	level=logging.DEBUG if debug_mode else logging.INFO,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

from app import app
#run_simple("127.0.0.1", 5000, app, threaded=True)
run_simple("0.0.0.0", 5000, app, threaded=True)
