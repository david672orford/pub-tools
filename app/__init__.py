import os
from flask import Flask

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
	SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/app.db' % os.path.abspath(app.instance_path),
	SQLALCHEMY_TRACK_MODIFICATIONS = False,
	SQLALCHEMY_ECHO = False,
	APP_DISPLAY_NAME = "JW Pubs",
	ENABLED_SUBAPPS = ['khplayer', 'toolbox', 'epub-viewer'],
	)
app.config.from_pyfile('config.py')
app.cachedir = os.path.join(app.instance_path, "cache")

from . import cli_update
from . import views
from . import subapps
from . import admin

