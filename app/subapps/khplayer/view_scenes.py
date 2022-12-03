from flask import Blueprint, render_template, request, redirect, flash
from time import sleep
import json

from ...utils import progress_callback_response, run_thread
from .views import blueprint
from .utils import obs, ObsError

@blueprint.route("/scenes/")
def page_scenes():
	try:
		scenes = reversed(obs.get_scene_list())
	except ObsError as e:
		flash("OBS: %s" % str(e))
		scenes = []

	return render_template(
		"khplayer/scenes.html",
		scenes = scenes,
		top = ".."
		)

@blueprint.route("/scenes/submit", methods=["POST"])
def page_scenes_submit():
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

	except ObsError as e:
		flash("OBS: %s" % str(e))

	if scene is not None:
		return progress_callback_response("Scene switched to %s" % scene)
	else:
		return redirect(".")
