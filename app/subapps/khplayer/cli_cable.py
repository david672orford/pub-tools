from flask import current_app
from flask.cli import AppGroup

from .utils.virtual_cable import patchbay, create_cable, destroy_cable, connect_peripherals, connect_obs, connect_zoom
from ...utils.config import get_config

cli_cable = AppGroup("cable", help="Virtual Audio Cable in Pipewire")

@cli_cable.command("create", help="Create the cable, but don't connect it to anything")
def cmd_cable_create():
	patchbay.load()
	create_cable(patchbay)

@cli_cable.command("destroy", help="Disconnect the cable and delete it")
def cmd_cable_destroy():
	patchbay.load()
	destroy_cable(patchbay)

@cli_cable.command("connect-peripherals", help="Connect microphone and speakers to cable")
def cmd_cable_connect_peripherals():
	config = get_config("PERIPHERALS")
	patchbay.load()
	connect_peripherals(patchbay, config)

@cli_cable.command("connect-obs", help="Connect OBS Studio's monitor output to cable")
def cmd_cable_connect_obs():
	patchbay.load()
	connect_obs(patchbay)

@cli_cable.command("connect-zoom", help="Connect Zoom's microphone input to cable")
def cmd_cable_connect_zoom():
	config = get_config("PERIPHERALS")
	patchbay.load()
	connect_zoom(patchbay, config)

@cli_cable.command("connect-all", help="Create cable and connect everything")
def cmd_cable_connect_all():
	config = get_config("PERIPHERALS")
	patchbay.load()
	connect_all(patchbay, config)

