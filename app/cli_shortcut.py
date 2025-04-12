"""CLI for creating application shortcuts"""

import os
import subprocess
from urllib.parse import urlparse, parse_qs
from hashlib import shake_128
import logging

from flask import current_app, render_template
from flask.cli import AppGroup
import click

logger = logging.getLogger(__name__)

cli_shortcut = AppGroup("shortcut", help="Application shortcut creation")

def init_app(app):
	app.cli.add_command(cli_shortcut)

@cli_shortcut.command("pub-tools")
@click.option("--start-menu", is_flag=True, help="Place in start menu rather than on desktop")
@click.option("--use-chrome", is_flag=True, help="Use Chrome or Chromium browser rather than Pywebview")
@click.argument("subapp")
def cmd_shortcut_pub_tools(start_menu, use_chrome, subapp):
	"""Create shortcut to a pub-tools subapp"""
	with current_app.app_context():
		root =  os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
		shortcut = render_template(
			"shortcuts/pub-tools.desktop",
			chrome_path = find_chrome() if use_chrome else None,
			pub_tools = os.path.join(root, "pub-tools"),
			icons = os.path.join(root, "icons"),
			name = current_app.blueprints[subapp].display_name,
			subapp = subapp,
			)
		print(shortcut)
		with open(os.path.join(get_install_dir(start_menu), f"pub-tools-{subapp}.desktop"), "w") as fh:
			fh.write(shortcut)

@cli_shortcut.command("zoom")
@click.option("--start-menu", is_flag=True, help="Place in start menu rather than on desktop")
@click.argument("name")
@click.argument("url")
def cmd_shortcut_zoom(start_menu, name, url):
	"""Create shortcut to a Zoom meeting"""
	parsed_url = urlparse(url)
	confno = parsed_url.path.split("/")[-1]
	pwd = parse_qs(parsed_url.query).get("pwd")[0]
	with current_app.app_context():
		shortcut = render_template(
			"shortcuts/start-meeting.desktop",
			name = name,
			confno = confno,
			pwd = pwd,
			)
	print(shortcut)
	with open(os.path.join(get_install_dir(start_menu), f"start-meeting-{confno}.desktop"), "w") as fh:
		fh.write(shortcut)

@cli_shortcut.command("web-browser")
@click.option("--start-menu", is_flag=True, help="Place in start menu rather than on desktop")
@click.option("--use-chrome", is_flag=True, help="Use Chrome or Chromium browser rather than Pywebview")
@click.argument("name")
@click.argument("url")
def cmd_shortcut_web_browser(start_menu, use_chrome, name, url):
	"""Create shortcut to a Zoom meeting"""
	root =  os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
	hash = shake_128(url.encode("utf8")).hexdigest(4)
	with current_app.app_context():
		shortcut = render_template(
			"shortcuts/web-browser.desktop",
			chrome_path = find_chrome() if use_chrome else None,
			name = name,
			url = url,
			web_browser = os.path.join(root, "web-browser"),
			icons = os.path.join(root, "icons"),
			)
	print(shortcut)
	with open(os.path.join(get_install_dir(start_menu), f"web-browser-{hash}.desktop"), "w") as fh:
		fh.write(shortcut)

def find_chrome():
	for item in ("/usr/bin/chromium-browser", "google-chrome"):
		if os.path.exists(item):
			return item
	else:
		raise AssertionError("Neither Chromium nor Chrome found")

def get_install_dir(start_menu:bool):
	if start_menu:
		return os.path.abspath(os.path.join(os.environ["HOME"], ".local", "share", "applications"))
	else:
		return subprocess.check_output(["xdg-user-dir", "DESKTOP"]).decode("utf-8").strip()
