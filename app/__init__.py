import os
import sys
import uuid
from importlib import import_module
from glob import glob
from shutil import rmtree
import logging

from flask import Flask, session
from jsonschema import validate as jsonschema_validate

from .utils.background import turbo
from .utils.babel import init_babel, compile_babel_catalogs

logger = logging.getLogger(__name__)

def create_app():
	if sys.platform == "win32":
		instance_path = os.path.join(os.environ["LOCALAPPDATA"], "Pub-Tools")
	else:
		instance_path = None	# default next to "app"

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

		# Database settings
		SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/pub-tools.db' % os.path.abspath(app.instance_path),
		SQLALCHEMY_TRACK_MODIFICATIONS = False,
		SQLALCHEMY_ECHO = False,

		# Cache settings
		WHOOSH_PATH = os.path.join(os.path.abspath(app.instance_path), "whoosh"),
		MEDIA_CACHEDIR = os.path.join(app.instance_path, "cache", "media"),
		GDRIVE_CACHEDIR = os.path.join(app.instance_path, "cache", "gdrive"),
		FLASK_CACHEDIR = os.path.join(app.instance_path, "cache", "flask"),

		# Pub Tools includes several subapps which can be enabled or disabled
		ENABLED_SUBAPPS = [
			"khplayer",
			"toolbox",
			"epubs",
			#"admin",
			],

		# Settings for all subapps
		UI_LANGUAGE = None,				# language of the user interface
		PUB_LANGUAGE = None,			# language in which to load publications from JW.ORG

		# Settings for the KH Player subapp
		THEME = None,					# TODO: implement in other subapps
		SUB_LANGUAGE = None,			# choose language to enable video subtitles
		VIDEO_RESOLUTION = "720p",		# resolution of videos from JW.ORG
		OBS_BROWSER_DOCK_SCALE = 1.0,	# font size when running on OBS browser dock
		CAMERA_NAME_OVERRIDES = {},		# friendly names of V4L cameras
		VIDEO_REMOTES = {},				# remote video feeds using VDO.Ninja
		PATCHBAY = True,				# show the Patchbay tab (if supported)
		SLIDES_DIR = os.path.abspath(os.path.join(app.instance_path, "slides")),
		)

	# Overlay with configuration from instance/config.py
	app.config.from_pyfile("config.py")

	# Apply default language settings
	if app.config["UI_LANGUAGE"] is None:
		try:
			# If we are running under OBS, get the locale from OBS
			import obspython as obs
			app.config["UI_LANGUAGE"] = obs.obs_get_locale().split("-")[0]
		except ImportError:		# not running under OBS
			# Get locale from the user's login session
			import locale
			lang = locale.getlocale()[0].split("_")[0]
			if sys.platform == "win32":		# FIXME: this is a temporary hack to get things working
				lang = {
					"English":"en",
					"Russian":"ru",
					}[lang]
			app.config["UI_LANGUAGE"] = lang
	if app.config["PUB_LANGUAGE"] is None:
		app.config["PUB_LANGUAGE"] = app.config["UI_LANGUAGE"]

	# Validate the final configuration using jsonschema
	# https://github.com/python-jsonschema/jsonschema
    # https://json-schema.org/learn/getting-started-step-by-step
	jsonschema_validate(instance=app.config, schema = {
		"type": "object",
		"properties": {
			"APP_DISPLAY_NAME": { "type": "string" },
			"FLASK_ADMIN_FLUID_LAYOUT": { "type": "boolean" },
			"SQLALCHEMY_DATABASE_URI": { "type": "string", "format": "uri" },
			"SQLALCHEMY_TRACK_MODIFICATIONS": { "type": "boolean" },
			"SQLALCHEMY_ECHO": { "type": "boolean" },
			"WHOOSH_PATH": { "type": "string" },
			"MEDIA_CACHEDIR": { "type": "string" },
			"GDRIVE_CACHEDIR": { "type": "string" },
			"SECRET_KEY": {
				"type": "string",
				"minLength": 16,
			},
			"ENABLED_SUBAPPS": {
				"type": "array",
				"minItems": 1,
				"items": {
					"type": "string",
					"enum": ["khplayer", "toolbox", "epubs", "admin"],
				},
			},
			"THEME": {
				"type": ["string", "null"],
				"enum": ["basic-light", "basic-dark", "colorful", None],
			},
			"UI_LANGUAGE": {
				"type": "string",
				"minLength": 2,
				"maxLength": 2,
			},
			"PUB_LANGUAGE": {
				"type": "string",
				"minLength": 2,
				"maxLength": 2,
			},
			"SUB_LANGUAGE": {
				"type": ["string", "null"],
				"minLength": 2,
				"maxLength": 2,
			},
			"VIDEO_RESOLUTION": {
				"type": "string",
				"enum": ["240p", "360p", "480p", "720p"],
			},
			"OBS_BROWSER_DOCK_SCALE": {
				"type": "number",
				"minimum": 1.0,
				"maximum": 5.0,
			},
			"PATCHBAY": {
				"enum": [False, True, "virtual-cable"],
			},
			"CAMERA_NAME_OVERRIDES": {
				"type": "object",
				"additionalProperties": {
					"type": "string",
					"minLength": 1,
				}
			},
			"VIDEO_REMOTES": {
				"type": "object",
				"additionalProperties": {
					"type": "object",
					"properties": {
						"view": {
							"type": "string",
						},
					},
					"required": ["view"],
					"additionalProperties": False,
				},
				"JWSTREAM_UPDATES": {
					"type": "string",
					"format": "uri",
				}
			},
		},
		# Disabled because Flask inserts many config items of its own
		#"additionalProperties": False,
	})

	# Init DB
	with app.app_context():
		from .models import init_app as models_init_app
		models_init_app(app)

	# Initialize Babel
	compile_babel_catalogs()
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
		for module_name in ("views", "subapps", "cli", "cli_jworg", "cli_cache", "cli_shortcut"):
			logger.debug("Loading module %s..." % module_name)
			module = import_module("app.%s" % module_name)
			module.init_app(app)

	# Create the directory to which we download media.
	if not os.path.exists(app.config["MEDIA_CACHEDIR"]):
		old_media_cachedir = os.path.join(app.instance_path, "media-cache")
		if os.path.exists(old_media_cachedir):
			logger.info("Moving media cache %s -> %s", old_media_cachedir, app.config["MEDIA_CACHEDIR"])
			os.rename(old_media_cachedir, app.config["MEDIA_CACHEDIR"])
		else:
			os.makedirs(app.config["MEDIA_CACHEDIR"])

	if not os.path.exists(app.config["GDRIVE_CACHEDIR"]):
		os.makedirs(app.config["GDRIVE_CACHEDIR"])

	# Remove cache directories from old versions of Pub-Tools
	for old_cache in glob(f"{app.instance_path}/*-cache"):
		logger.info("Deleting old cache dir %s", old_cache)
		rmtree(old_cache)

	return app
