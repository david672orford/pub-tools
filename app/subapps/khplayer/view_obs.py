from flask import Blueprint, render_template, request, redirect, flash
from time import sleep

from .views import blueprint, obs_connect, ObsError, run_thread
from ... import app, turbo

@blueprint.route("/obs/")
def page_obs():
	obs = obs_connect()
	if obs is None:
		scenes = []
	else:
		print(obs, obs.ws)
		scenes = reversed(obs.get_scene_list())
	return render_template("khplayer/obs.html", scenes=scenes, top="..")

@blueprint.route("/obs/submit", methods=["POST"])
def page_obs_submit():
	action = request.form.get("action")
	print("action:", action)

	obs = obs_connect()

	if obs is None:
		pass

	elif action == "delete":
		for scene in request.form.getlist("del"):
			print(scene)
			try:
				obs.remove_scene(scene)
			except ObsError as e:
				flash(str(e))
		sleep(1)

	elif action == "delete-all":
		for scene in obs.get_scene_list():
			try:
				obs.remove_scene(scene["sceneName"])
			except ObsError as e:
				flash(str(e))
		sleep(1)

	elif action == "new":
		collection = request.form.get("collection").strip()
		if collection != "":
			try:
				obs.create_scene_collection(collection)
			except ObsError as e:
				flash(str(e))

	return redirect(".")

