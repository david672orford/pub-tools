import os
from flask import Flask
from turbo_flask import Turbo

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

turbo = Turbo()
turbo.init_app(app)

app.cachedir = os.path.join(app.instance_path, "cache")
if not os.path.exists(app.cachedir):
	os.mkdir(app.cachedir)

# The Flask-Admin interface is not actually needed.
try:
	from . import admin
except ModuleNotFound:
	pass

from . import views
from . import subapps
from . import cli_update

