import os, uuid, platform
from importlib import import_module
from flask import Flask, session
#from turbo_flask import Turbo
from .turbo_sse import Turbo

def create_app(instance_path=None):
	global turbo

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
		CACHEDIR = os.path.join(app.instance_path, "cache")
		)
	app.config.from_pyfile("config.py")

	# Create the directory to which we download media.
	if not os.path.exists(app.config["CACHEDIR"]):
		os.mkdir(app.config["CACHEDIR"])

	@app.before_request
	def set_sessionid():
		if not "session-id" in session:
			session["session-id"] = uuid.uuid4().hex
		print("Session ID:", session["session-id"])

	turbo = Turbo()
	turbo.init_app(app)

	@turbo.user_id
	def get_session_id():
		return session["session-id"]

	with app.app_context():
		for module_name in ("models", "views", "admin", "subapps", "cli_update"):
			module = import_module("app.%s" % module_name)
			module.init_app(app)

	return app

