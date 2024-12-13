"""
CLI for Zoom integration
"""

import os
from configparser import ConfigParser

from flask.cli import AppGroup
import click

cli_zoom = AppGroup("zoom", help="Zoom conferencing integration")

@cli_zoom.command("configure")
def cmd_zoom_configure():
	"""Change Zoom settings to work with KHPlayer"""
	zoom_configfile = os.path.join(os.environ["HOME"], ".config", "zoomus.conf")
	tmpfile = "." + zoom_configfile
	backup_file = zoom_configfile + "~"

	# Load Zoom's configuration
	config = ConfigParser()
	config.read(zoom_configfile)

	# https://askubuntu.com/questions/1388053/what-are-all-of-the-available-zoomus-conf-options
	config.set("General", "showSystemTitlebar", "true")
	config.set("General", "enableMiniWindow", "false")

	# Save the modified config
	with open(tmpfile, "w") as fh:
		config.write(fh)
	if False:
		if os.path.exists(backup_file):
			os.remove(backup_file)
		os.rename(tmpfile, zoom_configfile)

@cli_zoom.command("tracker-test")
@click.argument("filename")
def cmd_zoom_tracker_test(filename):
	"""Run the tracker on a screenshot file and show result"""
	from .utils.zoom_tracker import tracker_test
	tracker_test(filename)
