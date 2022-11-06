#! /usr/bin/python3
# Run JW-Pubs as a standalone web server
# Connect your own browser to http://127.0.0.1:5000

import sys
import logging

debug_mode = (len(sys.argv) >= 2 and sys.argv[1] == '--debug')

logging.basicConfig(
	level=logging.DEBUG if debug_mode else logging.INFO,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

from app import app

if False:
	from werkzeug.middleware.proxy_fix import ProxyFix
	from werkzeug.serving import run_simple
	from app.werkzeug_logging import MyWSGIRequestHandler
	app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)
	run_simple('127.0.0.1', 5000, app, request_handler=MyWSGIRequestHandler, threaded=True)
else:
	from app import socketio
	socketio.run(app, host="127.0.0.1", port=5000)

