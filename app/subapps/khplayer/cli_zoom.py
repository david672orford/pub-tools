"""
CLI for Zoom integration
"""

import os
from configparser import ConfigParser

from flask.cli import AppGroup
import click

cli_zoom = AppGroup("zoom", help="Zoom conferencing integration")

@cli_zoom.command("setup")
def cmd_zoom_setup():
	"""Perform initial setup of Zoom to work with KHPlayer"""

	zoom_configfile = os.path.join(os.environ["HOME"], ".config", "zoomus.conf")
	tmpfile = zoom_configfile + ".tmp"
	backup_file = zoom_configfile + "~"

	# Load Zoom's configuration
	config = ConfigParser(strict=False)
	config.optionxform = str
	config.read(zoom_configfile, encoding="utf-8-sig")

	# https://askubuntu.com/questions/1388053/what-are-all-of-the-available-zoomus-conf-options
	config.set("General", "showSystemTitlebar", "true")
	config.set("General", "enableMiniWindow", "false")

	# Save the modified config
	with open(tmpfile, "w") as fh:
		config.write(fh)
		if os.path.exists(backup_file):
			os.remove(backup_file)
		os.rename(tmpfile, zoom_configfile)

@cli_zoom.command("tracker-test")
@click.argument("filename")
def cmd_zoom_tracker_test(filename):
	"""Run the tracker on a screenshot file and show result"""
	from .utils.zoom_tracker_tests import tracker_test_image
	tracker_test_image(filename)

@cli_zoom.command("track")
def cmd_zoom_track():
	"""Run the Zoom tracker from outside OBS through OBS-Websocket"""
	from .utils.zoom_tracker_tests import tracker_track
	tracker_track()

