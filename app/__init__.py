import os
from flask import Flask

app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
	SQLALCHEMY_DATABASE_URI = 'sqlite:///%s/app.db' % os.path.abspath(app.instance_path),
	SQLALCHEMY_TRACK_MODIFICATIONS = False,
	ENABLED_SUBAPPS = ['toolbox', 'obs'],
	)
app.config.from_pyfile('config.py')
app.cachedir = os.path.join(app.instance_path, "cache")

from . import pubs_loader
from . import views

