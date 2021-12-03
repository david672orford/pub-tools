#! /usr/bin/env python3

# For Apache Mod_Wsgi
if __name__.startswith("_mod_wsgi_"):
	import os, sys
	sys.path.insert(0, os.path.dirname(__file__))

import sys
import logging
from app import app
from app.subapps import load_subapps

debug_mode = (len(sys.argv) >= 2 and sys.argv[1] == '--debug')
logging.basicConfig(level=logging.DEBUG if debug_mode else logging.INFO)

load_subapps()

# For Docker or for standalone testing
if __name__ == "__main__":
	from werkzeug.serving import run_simple
	from werkzeug.middleware.proxy_fix import ProxyFix
	app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_for=1)
	run_simple('0.0.0.0', 5000, app, threaded=True)
