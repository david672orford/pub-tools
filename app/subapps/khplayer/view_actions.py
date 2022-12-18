from flask import current_app, Blueprint, render_template, request, redirect, flash
from time import sleep
import json
import subprocess

from .views import blueprint
from .utils import obs, ObsError
from .view_patchbay import patchbay
from .start_meeting import start_meeting
from .virtual_cable import connect_all, destroy_cable

@blueprint.route("/actions/")
def page_actions():
	try:
		virtual_camera_status = obs.get_virtual_camera_status()
	except ObsError as e:
		flash("OBS: %s" % str(e))
		virtual_camera_status = None

	return render_template(
		"khplayer/actions.html",
		virtual_camera_status = virtual_camera_status,
		top = ".."
		)

@blueprint.route("/actions/submit", methods=["POST"])
def page_actions_submit():
	try:
		match request.form.get("action"):

			case "start-meeting":
				projector_port = current_app.config["PERIPHERALS"].get("projector_port", "HDMI-0")
				subprocess.run(["xrandr", "--addmode", projector_port, "1920x1080"])
				subprocess.run(["xrandr", "--output", projector_port, "--mode", "1920x1080", "--right-of", "HDMI-1"])

				patchbay.load()
				connect_all(patchbay, current_app.config["PERIPHERALS"])

				start_meeting(current_app.config["ZOOM"])

			case "start-virtualcam":
				obs.set_virtual_camera_status(True)
	
			case "start-projector":
				obs.start_output_projector(1)

			case "connect-camera":
				obs.reconnect_camera(current_app.config["PERIPHERALS"]["camera"])

			case "connect-audio":
				patchbay.load()
				connect_all(patchbay, current_app.config["PERIPHERALS"])

			case "disconnect-audio":
				patchbay.load()
				destroy_cable(patchbay)

	except ObsError as e:
		flash("OBS: %s" % str(e))

	return redirect(".")

