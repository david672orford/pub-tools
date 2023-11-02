from .admin import admin

def init_app(app, url_prefix):
	admin.name = app.config['APP_DISPLAY_NAME']
	admin.init_app(app)
	blueprint = app.blueprints["admin"]
	blueprint.display_name = "DB Admin"
	blueprint.blurb = "Access to the database used by Pub-Tools"

