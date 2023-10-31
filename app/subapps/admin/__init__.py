from flask import Blueprint
from .admin import admin

def init_app(app, url_prefix):

	# FIXME: It would be better to get Flask-Admin inside this blueprint
	blueprint = Blueprint("admin_dummy", __name__)
	blueprint.display_name = "DB Admin"
	blueprint.blurb = "Access to the database used by Pub-Tools"
	app.register_blueprint(blueprint, url_prefix=url_prefix)

	admin.name = app.config['APP_DISPLAY_NAME']
	admin.init_app(app)

