from flask import Blueprint, render_template, request, redirect, flash
from time import sleep
import json

from ... import app, run_thread
from .views import blueprint
from .utils import obs, ObsError

@blueprint.route("/obs/")
def page_obs():
	try:
		scenes = reversed(obs.get_scene_list())
		virtual_camera_status = obs.get_virtual_camera_status()
	except ObsError as e:
		flash("OBS: %s" % str(e))
		scenes = []
		virtual_camera_status = None

	return render_template(
		"khplayer/obs.html",
		scenes = scenes,
		virtual_camera_status = virtual_camera_status,
		top = ".."
		)

@blueprint.route("/obs/submit", methods=["POST"])
def page_obs_submit():
	action = request.form.get("action")
	scene = request.form.get("scene")
	print("action:", action)

	try:
		if scene is not None:
			obs.set_current_program_scene(scene)
	
		elif action == "delete":
			for scene in request.form.getlist("del"):
				print(scene)
				try:
					obs.remove_scene(scene)
				except ObsError as e:
					flash(str(e))
			sleep(1)
	
		elif action == "start-virtualcam":
			obs.set_virtual_camera_status(True)
	
		elif action == "stop-virtualcam":
			obs.set_virtual_camera_status(False)
	
		elif action == "start-projector":
			obs.start_output_projector(1)

	except ObsError as e:
		flash("OBS: %s" % str(e))

	return redirect(".")

