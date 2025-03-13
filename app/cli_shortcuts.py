"""CLI for creating application shortcuts"""

import os
import subprocess
from urllib.parse import urlparse, parse_qs
import logging

from flask import current_app, render_template
from flask.cli import AppGroup
import click

logger = logging.getLogger(__name__)

cli_shortcuts = AppGroup("shortcuts", help="Application shortcut creation")

def init_app(app):
	app.cli.add_command(cli_shortcuts)

@cli_shortcuts.command("pub-tools")
@click.option("--start-menu", is_flag=True, help="Place in start menu rather than on desktop")
@click.option("--chromium", is_flag=True, help="Use Chromium browser rather than Pywebview")
@click.argument("subapp")
def cmd_shortcuts_pub_tools(start_menu, chromium, subapp):
	"""Create shortcut to a pub-tools subapp"""
	with current_app.app_context():
		root =  os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
		shortcut = render_template(
			"shortcuts/pub-tools.desktop",
			chromium = chromium,
			pub_tools = os.path.join(root, "pub-tools"),
			icons = os.path.join(root, "icons"),
			name = current_app.blueprints[subapp].display_name,
			subapp = subapp,
			)
		print(shortcut)
		with open(os.path.join(get_install_dir(start_menu), f"pub-tools-{subapp}.desktop"), "w") as fh:
			fh.write(shortcut)

@cli_shortcuts.command("zoom")
@click.option("--start-menu", is_flag=True, help="Place in start menu rather than on desktop")
@click.argument("name")
@click.argument("url")
def cmd_shortcuts_zoom(start_menu, subapp):
	"""Create shortcut to a Zoom meeting"""
	parsed_url = urlparse(url)
	confno = parsed_url.path.split("/")[-1]
	pwd = parse_qs(parsed_url.query).get("pwd")
	with current_app.app_context():
		shortcut = render_template(
			"shortcuts/pub-tools.desktop",
			name = name,
			confno = confno,
			pwd = pwd,
		)
	print(shortcut)
	with open(os.path.join(get_install_dir(start_menu), f"start-meeting-{confno}.desktop"), "w") as fh:
		fh.write(shortcut)

def get_install_dir(start_menu:bool):
	if start_menu:
		return os.path.abspath(os.path.join(os.environ["HOME"], ".local", "share", "applications"))
	else:
		return subprocess.check_output(["xdg-user-dir", "DESKTOP"]).decode("utf-8").strip()
