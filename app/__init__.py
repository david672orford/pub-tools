import os, uuid, platform
from importlib import import_module
from flask import Flask, session
import logging

from .utils import turbo
from .utils.babel import init_babel

logger = logging.getLogger(__name__)

def create_app(instance_path=None):
	app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

	# If we don't have a config file yet, create one
	if not os.path.exists(app.instance_path):
		import secrets
		os.mkdir(app.instance_path)
		with open(os.path.join(app.instance_path, "config.py"), "w") as cf:
			cf.write('SECRET_KEY = "%s"\n' % secrets.token_hex())

	# Set up default configuration
	app.config.from_mapping(
		SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/pub-tools.db' % os.path.abspath(app.instance_path),
		SQLALCHEMY_TRACK_MODIFICATIONS = False,
		SQLALCHEMY_ECHO = False,
		WHOOSH_PATH = os.path.join(os.path.abspath(app.instance_path), "whoosh"),
		FLASK_ADMIN_FLUID_LAYOUT = True,
		APP_DISPLAY_NAME = "JW Pubs",
		ENABLED_SUBAPPS = ["khplayer", "toolbox", "epubs"],
		CACHEDIR = os.path.join(app.instance_path, "cache"),
		PUB_LANGUAGE = "ru",
		SUB_LANGUAGE = None,
		VIDEO_RESOLUTION = "480p",
		PERIPHERALS = {}
		)

	# Overlay with configuration from instance/config.py
	app.config.from_pyfile("config.py")

	# Init DB and load more configuration
	# (May override settings loaded above.)
	with app.app_context():
		from .models import init_app as models_init_app, Config
		models_init_app(app)
		for config in Config.query:
			app.config[config.name] = config.data

	# Initialize Babel
	init_babel(app)

	# Accept SSE connection from Hotwire Turbo running in the browser
	turbo.init_app(app)

	@app.before_request
	def set_sessionid():
		if not "session-id" in session:
			session["session-id"] = uuid.uuid4().hex
		#print("Session ID:", session["session-id"])

	@turbo.user_id
	def get_session_id():
		return session["session-id"]

	# Load, initialize, and connect app components
	with app.app_context():
		for module_name in ("views", "admin", "subapps", "cli_update", "cli_cache"):
			logger.debug("Loading module %s..." % module_name)
			try:
				module = import_module("app.%s" % module_name)
				module.init_app(app)
			except ModuleNotFoundError as e:
				if module_name == "admin":
					logger.info("module %s disabled due to unsatisfied dependencies" % module_name)
				else:
					raise e

	# Create the directory to which we download media.
	if not os.path.exists(app.config["CACHEDIR"]):
		os.mkdir(app.config["CACHEDIR"])

	return app

