from flask import current_app
from flask.cli import AppGroup

from .utils.pipewire import Patchbay
from .utils.virtual_cable import create_cable, destroy_cable, \
	connect_peripherals, connect_obs, connect_zoom, connect_all
from ...utils.config import get_config

cli_cable = AppGroup("cable", help="Virtual Audio Cable in Pipewire")

@cli_cable.command("create")
def cmd_cable_create():
	"""Create the cable, but don't connect it to anything"""
	patchbay = Patchbay()
	patchbay.load()
	create_cable(patchbay)

@cli_cable.command("destroy")
def cmd_cable_destroy():
	"""Disconnect the cable and delete it"""
	patchbay = Patchbay()
	patchbay.load()
	destroy_cable(patchbay)

@cli_cable.command("connect-peripherals")
def cmd_cable_connect_peripherals():
	"""Connect microphone and speakers to cable"""
	config = get_config("PERIPHERALS")
	patchbay = Patchbay()
	patchbay.load()
	connect_peripherals(patchbay, config)

@cli_cable.command("connect-obs")
def cmd_cable_connect_obs():
	"""Connect OBS Studio's monitor output to cable"""
	patchbay = Patchbay()
	patchbay.load()
	connect_obs(patchbay)

@cli_cable.command("connect-zoom")
def cmd_cable_connect_zoom():
	"""Connect Zoom's microphone input to cable"""
	config = get_config("PERIPHERALS")
	patchbay = Patchbay()
	patchbay.load()
	connect_zoom(patchbay, config)

@cli_cable.command("connect-all")
def cmd_cable_connect_all():
	"""Create cable and connect everything"""
	config = get_config("PERIPHERALS")
	patchbay = Patchbay()
	patchbay.load()
	connect_all(patchbay, config)
