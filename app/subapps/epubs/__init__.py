def init_app(app, url_prefix):
	from .views import blueprint
	app.register_blueprint(blueprint, url_prefix=url_prefix)
	from .cli import cli_epubs
	app.cli.add_command(cli_epubs)
