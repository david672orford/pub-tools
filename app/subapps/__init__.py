import os
import logging
from importlib import import_module
from app import app

logger = logging.getLogger(__name__)

# From each component subdirectory load a Flask blueprint and some Flask-Admin views.
for subapp_name in app.config['ENABLED_SUBAPPS']:
	logger.info("Importing blueprint for %s subapp..." % subapp_name)
	subapp_module = import_module("app.subapps.%s" % subapp_name)
	app.register_blueprint(subapp_module.blueprint, url_prefix="/%s" % subapp_name)
	#import_module("app.subapps.%s.admin" % subapp_name)
