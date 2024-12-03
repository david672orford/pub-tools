import os
from .utils.runningtime import time_to_str
from .utils.theme import get_theme

menu = []

def init_app(app, url_prefix):

	app.jinja_env.globals["menu"] = menu
	app.jinja_env.filters["runningtime"] = time_to_str
	app.jinja_env.globals["get_theme"] = get_theme

	from .views import blueprint
	blueprint.cache.init_app(app, {
		#"CACHE_TYPE": "SimpleCache",
		"CACHE_TYPE": "FileSystemCache",
		"CACHE_DIR": os.path.join(app.instance_path, "flask-cache"),
		})
	app.register_blueprint(blueprint, url_prefix=url_prefix)

	# FIXME: There must be a better way to make the app available to
	# the event handlers in view_scenes.py.
	blueprint.app = app

	from .utils.controllers import obs
	obs.init_app(app)

	from .cli_obs import cli_obs
	app.cli.add_command(cli_obs)

	from .cli_cable import cli_cable
	app.cli.add_command(cli_cable)

	from .cli_zoom import cli_zoom
	app.cli.add_command(cli_zoom)
