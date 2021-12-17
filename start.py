#! /usr/bin/env python3

# For Apache Mod_Wsgi
if __name__.startswith("_mod_wsgi_"):
	import os, sys
	sys.path.insert(0, os.path.dirname(__file__))

import sys
import logging, logging.config

debug_mode = (len(sys.argv) >= 2 and sys.argv[1] == '--debug')

logging.config.dictConfig({
	'version': 1,
	'formatters': {'default': {'format': '%(levelname)s:%(name)s:%(message)s'}},
	'handlers': {
		'wsgi': {
			'class': 'logging.StreamHandler',
			'stream': 'ext://flask.logging.wsgi_errors_stream',
			'formatter': 'default'
			}
		},
	'root': {
		'level': 'DEBUG' if debug_mode else 'WARNING',
		'handlers': ['wsgi']
		},
	'loggers': {
		'werkzeug': {
			'level': 'DEBUG' if debug_mode else 'INFO',
			},
		'app.subapps.epubs': {
			'level': 'DEBUG',
			},
		}

	})

from app import app

# Show levels settings of all the loggers
for logger_name, logger in logging.root.manager.loggerDict.items():
	print("Logger", logger_name, logging.getLevelName(getattr(logger, "level", None)))

# For Docker or for standalone testing
if __name__ == "__main__":
	from werkzeug.serving import run_simple
	from werkzeug.middleware.proxy_fix import ProxyFix
	app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)
	run_simple('0.0.0.0', 5000, app, threaded=True)

