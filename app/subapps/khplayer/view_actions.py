from flask import current_app, Blueprint, render_template, request, redirect, flash
from time import sleep
import os, json, subprocess

from .views import blueprint
from .utils import obs, ObsError
from .view_patchbay import patchbay
from .cameras import get_camera_dev
from .zoom import start_meeting, find_second_window
from .virtual_cable import connect_all, destroy_cable
from ...utils import progress_callback

zoom_proc = None
obs_proc = None

@blueprint.route("/actions/")
def page_actions():
	try:
		virtual_camera_status = obs.get_virtual_camera_status()
	except ObsError as e:
		flash("OBS: %s" % str(e))
		virtual_camera_status = None

	return render_template(
		"khplayer/actions.html",
		zoom_running = (zoom_proc is not None and zoom_proc.poll() is None),
		obs_running = (obs_proc is not None and obs_proc.poll() is None),
		virtual_camera_status = virtual_camera_status,
		top = ".."
		)

@blueprint.route("/actions/submit", methods=["POST"])
def page_actions_submit():
	global zoom_proc
	global obs_proc
	try:
		match request.form.get("action"):

			case "start-meeting":
				#projector_port = current_app.config["PERIPHERALS"].get("projector_port", "HDMI-0")
				#subprocess.run(["xrandr", "--addmode", projector_port, "1920x1080"])
				#subprocess.run(["xrandr", "--output", projector_port, "--mode", "1920x1080", "--right-of", "HDMI-1"])

				patchbay.load()
				connect_all(patchbay, current_app.config["PERIPHERALS"])

				try:
					zoom_proc = start_meeting(current_app.config["ZOOM"], os.path.join(current_app.instance_path, "zoom.log"))
				except Exception as e:
					flash(str(e))

			case "start-obs":
				patchbay.load()
				connect_all(patchbay, current_app.config["PERIPHERALS"])

				with open(os.path.join(current_app.instance_path, "obs.log"), "w") as fh:
					obs_proc = subprocess.Popen(["obs"], stderr=subprocess.STDOUT, stdout=fh)
				for i in range(25):
					try:
						obs.connect()
						progress_callback("OBS is running.")
						obs.set_virtual_camera_status(True)
						obs.start_output_projector(1)
						break
					except ObsError:
						progress_callback("Starting OBS: %d..." % i)
						sleep(1)

			case "start-virtualcam":
				obs.set_virtual_camera_status(True)
				sleep(1)
	
			case "start-projector":
				obs.start_output_projector(1)

			case "reconnect-camera":
				camera_dev = get_camera_dev()
				if camera_dev is not None:
					obs.reconnect_camera(camera_dev)

			case "reconnect-zoom-capture":
				capture_window = find_second_window()
				if capture_window is not None:
					obs.reconnect_zoom_input(capture_window)

			case "reconnect-audio":
				patchbay.load()
				for failure in connect_all(patchbay, current_app.config["PERIPHERALS"]):
					flash(failure)

			case "disconnect-audio":
				patchbay.load()
				destroy_cable(patchbay)

	except ObsError as e:
		flash("OBS: %s" % str(e))

	return redirect(".")

