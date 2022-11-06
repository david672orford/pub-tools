import os
from flask import Flask
from flask_socketio import SocketIO

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
	SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/app.db' % os.path.abspath(app.instance_path),
	SQLALCHEMY_TRACK_MODIFICATIONS = False,
	SQLALCHEMY_ECHO = False,
	ENABLED_SUBAPPS = ['toolbox', 'obs', 'epubs'],
	)
app.config.from_pyfile('config.py')
app.cachedir = os.path.join(app.instance_path, "cache")

socketio = SocketIO(app, logger=True, engineio_logger=True)

from . import cli_update
from . import views
from . import subapps

