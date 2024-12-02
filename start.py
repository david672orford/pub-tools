#! /usr/bin/python3
"""
This script runs Pub-Tools in a standalone web server.

Start it:
   ./start.py

Then browser to:
   http://127.0.0.1:5000
"""

from venv_tool import activate
activate()

import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from werkzeug.serving import run_simple

from app import create_app
from app.utils.clean_logs import CleanlogWSGIRequestHandler

parser = ArgumentParser(
	description = __doc__,
	formatter_class = RawDescriptionHelpFormatter,
	)
parser.add_argument("--debug", action="store_true")
parser.add_argument("--debug-requests", action="store_true")
parser.add_argument("--listen-addr", default="127.0.0.1")
parser.add_argument("--listen-port", type=int, default=5000)
options = parser.parse_args()

logging.basicConfig(
	level=logging.DEBUG if options.debug else logging.INFO,
	format='%(asctime)s.%(msecs)03d %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

if options.debug_requests:
	from http.client import HTTPConnection
	HTTPConnection.debuglevel = 1

app = create_app()
run_simple(
	options.listen_addr, options.listen_port,
	app, request_handler=CleanlogWSGIRequestHandler, threaded=True
	)
