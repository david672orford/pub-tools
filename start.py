#! /usr/bin/env python3

# For Apache Mod_Wsgi
if __name__.startswith("_mod_wsgi_"):
	import os, sys
	sys.path.insert(0, os.path.dirname(__file__))

import sys
import logging

debug_mode = (len(sys.argv) >= 2 and sys.argv[1] == '--debug')

logging.basicConfig(
	level=logging.DEBUG if debug_mode else logging.WARN,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

from app import app

# Show levels settings of all the loggers
for logger_name, logger in logging.root.manager.loggerDict.items():
	if type(logger) is logging.PlaceHolder:
		print("Logger", logger_name)
	else:
		print("Logger", logger_name, logging.getLevelName(logger.level), logging.getLevelName(logger.getEffectiveLevel()))

# For Docker or for standalone testing
if __name__ == "__main__":
	from werkzeug.serving import run_simple
	from werkzeug.middleware.proxy_fix import ProxyFix
	from app.werkzeug_logging import MyWSGIRequestHandler
	app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)
	run_simple('0.0.0.0', 5000, app, request_handler=MyWSGIRequestHandler, threaded=True)

