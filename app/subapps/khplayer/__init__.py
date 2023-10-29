menu = []

def init_app(app, url_prefix):
	app.jinja_env.globals["menu"] = menu

	from .views import blueprint
	app.register_blueprint(blueprint, url_prefix=url_prefix)

	from .cli_obs import cli_obs
	app.cli.add_command(cli_obs)

	from .cli_cable import cli_cable
	app.cli.add_command(cli_cable)
