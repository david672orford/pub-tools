import os, uuid, platform
from importlib import import_module
from flask import Flask, session
import logging

from .utils.background import turbo
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
		APP_DISPLAY_NAME = "Pub Tools",
		FLASK_ADMIN_FLUID_LAYOUT = True,

		# Options are:
		# * basic-light
		# * basic-dark
		# * colorful (for testing)
		THEME = "basic-light",

		# Database and cache settings
		SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/pub-tools.db' % os.path.abspath(app.instance_path),
		SQLALCHEMY_TRACK_MODIFICATIONS = False,
		SQLALCHEMY_ECHO = False,
		WHOOSH_PATH = os.path.join(os.path.abspath(app.instance_path), "whoosh"),
		MEDIA_CACHEDIR = os.path.join(app.instance_path, "media-cache"),
		GDRIVE_CACHEDIR = os.path.join(app.instance_path, "gdrive-cache"),

		# Pub Tools includes several subapps which can be enabled or disabled
		ENABLED_SUBAPPS = [
			"khplayer",
			"toolbox",
			"epubs",
			#"admin",
			],

		# KH Player Settings
		UI_LANGUAGE = "en",
		PUB_LANGUAGE = "en",			# language in which to load publications from JW.ORG
		SUB_LANGUAGE = None,			# choose language to enable video subtitles
		VIDEO_RESOLUTION = "480p",		# resolution of videos from JW.ORG
		OBS_BROWSER_DOCK_SCALE = 1.0,	# font size when running on OBS browser dock
		VIDEO_REMOTES = {},				# remove video feeds using VDO.Ninja
		CAMERA_NAME_OVERRIDES = {},		# rename the V4L cameras
		PATCHBAY = "virtual-cable",
		)

	# Overlay with configuration from instance/config.py
	app.config.from_pyfile("config.py")

	# FIXME: there must be a better way to do this
	assert type(app.config["UI_LANGUAGE"]) is str
	assert type(app.config["PUB_LANGUAGE"]) is str
	assert type(app.config["SUB_LANGUAGE"]) in (str, type(None))
	assert app.config["VIDEO_RESOLUTION"] in ("240p", "360p", "480p", "720p")
	assert type(app.config["OBS_BROWSER_DOCK_SCALE"]) is float
	assert type(app.config["CAMERA_NAME_OVERRIDES"]) is dict
	assert type(app.config["VIDEO_REMOTES"]) is dict
	assert app.config["PATCHBAY"] in (False, True, "virtual-cable")

	# Init DB
	with app.app_context():
		from .models import init_app as models_init_app
		models_init_app(app)

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
		for module_name in ("views", "subapps", "cli_update", "cli_cache"):
			logger.debug("Loading module %s..." % module_name)
			module = import_module("app.%s" % module_name)
			module.init_app(app)

	# Create the directory to which we download media.
	if not os.path.exists(app.config["MEDIA_CACHEDIR"]):
		old_media_cachedir = os.path.join(app.instance_path, "cache")
		if os.path.isdir(old_media_cachedir):
			os.rename(old_media_cachedir, app.config["MEDIA_CACHEDIR"])
		else:
			os.mkdir(app.config["MEDIA_CACHEDIR"])

	return app

