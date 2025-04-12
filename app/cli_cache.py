"""CLI for managing the media cache"""

from flask.cli import AppGroup

from .utils.cache_maint import scan_cache

cli_cache = AppGroup("cache", help="Cache maintanance")

def init_app(app):
	app.cli.add_command(cli_cache)

@cli_cache.command("status")
def cmd_cache_status():
	"""Show cache usage"""
	scan_cache()

@cli_cache.command("clean")
def cmd_cache_clean():
	"""Remove old files from cache"""
	scan_cache(clean=True)
