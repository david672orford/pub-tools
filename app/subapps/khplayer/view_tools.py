from flask import Blueprint, render_template, request, redirect, flash
from time import sleep
import json

from ...utils import run_thread
from .views import blueprint
from .utils import obs, ObsError

@blueprint.route("/tools/")
def page_tools():
	try:
		virtual_camera_status = obs.get_virtual_camera_status()
	except ObsError as e:
		flash("OBS: %s" % str(e))
		virtual_camera_status = None

	return render_template(
		"khplayer/tools.html",
		virtual_camera_status = virtual_camera_status,
		top = ".."
		)

@blueprint.route("/tools/submit", methods=["POST"])
def page_obs_submit():
	action = request.form.get("action")
	scene = request.form.get("scene")
	print("action:", action)

	try:
		if action == "start-virtualcam":
			obs.set_virtual_camera_status(True)
	
		elif action == "stop-virtualcam":
			obs.set_virtual_camera_status(False)
	
		elif action == "start-projector":
			obs.start_output_projector(1)

	except ObsError as e:
		flash("OBS: %s" % str(e))

	return redirect(".")

