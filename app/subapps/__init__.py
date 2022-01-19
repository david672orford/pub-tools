import os
import logging
from importlib import import_module
from app import app

logger = logging.getLogger(__name__)

# From each subapp subdirectory load a Flask blueprint
subapps = app.config['ENABLED_SUBAPPS']
for subapp_name in subapps:
	logger.info("Importing blueprint for %s subapp..." % subapp_name)
	subapp_module = import_module("app.subapps.%s" % subapp_name)
	url_prefix = ("/"+subapp_name) if len(subapps) > 1 else "/"
	app.register_blueprint(subapp_module.blueprint, url_prefix=url_prefix)
