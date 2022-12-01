import os, uuid, platform
from flask import Flask, session

# On Windows we store our files in the user's AppData folder.
instance_path = None
if platform.system() == "Windows":
	appdata = os.environ.get("LOCALAPPDATA")
	if appdata:
		instance_path = os.path.join(appdata, "Pub-Tools")

app = Flask(__name__, instance_path=instance_path, instance_relative_config=True)

# If we don't have a config file yet, create one
if not os.path.exists(app.instance_path):
	import secrets
	os.mkdir(app.instance_path)
	with open(os.path.join(app.instance_path, "config.py"), "w") as cf:
		cf.write('SECRET_KEY = "%s"\n' % secrets.token_hex())

# Load the configuration
app.config.from_mapping(
	SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/pub-tools.db' % os.path.abspath(app.instance_path),
	SQLALCHEMY_TRACK_MODIFICATIONS = False,
	SQLALCHEMY_ECHO = False,
	FLASK_ADMIN_FLUID_LAYOUT = True,
	APP_DISPLAY_NAME = "JW Pubs",
	ENABLED_SUBAPPS = ["khplayer", "toolbox", "epubs"],
	PUB_LANGUAGE = "ru",
	)
app.config.from_pyfile("config.py")

# Create the directory to which we download media.
app.cachedir = app.config.get("CACHEDIR")
if app.cachedir is None:
	app.cachedir = os.path.join(app.instance_path, "cache")
if not os.path.exists(app.cachedir):
	os.mkdir(app.cachedir)

# Try to load the admin interface. This will fail if Flask-Admin
# is not installed. We ignore failure since the admin interface
# is of use only to the developers.
try:
	from . import admin
except ModuleNotFoundError:
	pass

from .turbo import turbo
from .utils import *
from . import views
from . import subapps
from . import cli_update

