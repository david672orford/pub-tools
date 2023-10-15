from flask import current_app
from flask.cli import AppGroup

from .utils.virtual_cable import patchbay, create_cable, destroy_cable, connect_peripherals, connect_obs, connect_zoom

cli_cable = AppGroup("cable", help="Virtual Audio Cable")

@cli_cable.command("create")
def cmd_cable_create():
	patchbay.load()
	create_cable(patchbay)

@cli_cable.command("destroy")
def cmd_cable_destroy():
	patchbay.load()
	destroy_cable(patchbay)

@cli_cable.command("connect-peripherals")
def cmd_cable_connect_peripherals():
	patchbay.load()
	connect_peripherals(patchbay, current_app.config["PERIPHERALS"])

@cli_cable.command("connect-obs")
def cmd_cable_connect_obs():
	patchbay.load()
	connect_obs(patchbay)

@cli_cable.command("connect-zoom")
def cmd_cable_connect_zoom():
	patchbay.load()
	connect_zoom(patchbay)

@cli_cable.command("connect-all")
def cmd_cable_connect_all():
	patchbay.load()
	connect_all(patchbay, current_app.config["PERIPHERALS"])

