import os

menu = []

def init_app(app, url_prefix):

	app.jinja_env.globals["menu"] = menu

	from .views import blueprint
	blueprint.cache.init_app(app, {
		#"CACHE_TYPE": "SimpleCache",
		"CACHE_TYPE": "FileSystemCache",
		"CACHE_DIR": os.path.join(app.instance_path, "flask-cache"),
		})
	app.register_blueprint(blueprint, url_prefix=url_prefix)

	from .view_scenes import scene_event_handler
	scene_event_handler.app = app

	from .cli_obs import cli_obs
	app.cli.add_command(cli_obs)

	from .cli_cable import cli_cable
	app.cli.add_command(cli_cable)

