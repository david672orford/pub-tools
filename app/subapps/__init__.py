import os
import logging
from importlib import import_module

logger = logging.getLogger(__name__)

def init_app(app):
	# From each subapp subdirectory load a Flask blueprint
	subapps = app.config["ENABLED_SUBAPPS"]
	for subapp_name in subapps:
		logger.debug("Importing blueprint for %s subapp..." % subapp_name)
		subapp_module = import_module("app.subapps.%s" % subapp_name)
		url_prefix = ("/"+subapp_name)
		subapp_module.init_app(app, url_prefix)
