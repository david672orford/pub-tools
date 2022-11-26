import os
import uuid
from flask import Flask, session

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
	SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/pub-tools.db' % os.path.abspath(app.instance_path),
	SQLALCHEMY_TRACK_MODIFICATIONS = False,
	SQLALCHEMY_ECHO = False,
	FLASK_ADMIN_FLUID_LAYOUT = True,
	APP_DISPLAY_NAME = "JW Pubs",
	ENABLED_SUBAPPS = ['khplayer', 'toolbox', 'epubs'],
	PUB_LANGUAGE = "ru",
	)
app.config.from_pyfile('config.py')

# Create the directory to which we download media.
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

from .turbo_ws import turbo
from .utils import *
from . import views
from . import subapps
from . import cli_update

