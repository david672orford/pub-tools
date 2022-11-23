from flask import Blueprint, render_template, request, redirect, flash
from time import sleep
import json

from .views import blueprint, obs_connect, ObsError, run_thread
from ... import app, turbo

@blueprint.route("/obs/")
def page_obs():
	obs = obs_connect()

	if obs is None:
		scenes = []
		virtualcam_status = None
	else:
		scenes = reversed(obs.get_scene_list())
		virtual_camera_status = obs.get_virtual_camera_status()

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

	obs = obs_connect()

	if obs is None:
		pass

	elif scene is not None:
		obs.set_current_program_scene(scene)

	elif action == "delete":
		for scene in request.form.getlist("del"):
			print(scene)
			try:
				obs.remove_scene(scene)
			except ObsError as e:
				flash(str(e))
		sleep(1)

	elif action == "create-collection":
		collection = request.form.get("collection").strip()
		if collection != "":
			try:
				obs.create_scene_collection(collection)
			except ObsError as e:
				flash(str(e))

	elif action == "start-virtualcam":
		obs.set_virtual_camera_status(True)

	elif action == "stop-virtualcam":
		obs.set_virtual_camera_status(False)

	elif action == "start-projector":
		obs.start_output_projector(1)

	return redirect(".")

