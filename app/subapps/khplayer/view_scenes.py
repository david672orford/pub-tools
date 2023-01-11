from flask import current_app, Blueprint, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
from time import sleep
import os, json

from ...utils import progress_callback_response, run_thread
from .views import blueprint
from .utils import obs, ObsError
from .zoom import find_second_window
from .cameras import get_camera_dev

@blueprint.route("/scenes/")
def page_scenes():
	try:
		scene_names = list(map(lambda scene: scene["sceneName"], reversed(obs.get_scene_list())))
	except ObsError as e:
		flash("OBS: %s" % str(e))
		scene_names = []

	return render_template(
		"khplayer/scenes.html",
		scene_names = scene_names,
		top = ".."
		)

@blueprint.route("/scenes/submit", methods=["POST"])
def page_scenes_submit():
	action = request.form.get("action")
	scene = request.form.get("scene")
	message = None
	print("action:", action)

	try:
		if scene is not None:
			obs.set_current_program_scene(scene)
			message = "Scene switched to %s" % scene
	
		elif action == "delete":
			for scene in request.form.getlist("del"):
				print(scene)
				try:
					obs.remove_scene(scene)
				except ObsError as e:
					flash(str(e))
			sleep(1)

		elif action == "add-camera":
			camera_dev = get_camera_dev()
			if camera_dev is not None:
				obs.create_camera_scene(camera_dev)
				sleep(1)

		elif action == "add-zoom":
			capture_window = find_second_window()
			if capture_window is not None:
				obs.create_zoom_scene(capture_window)
				sleep(1)

		elif action == "add-split":
			camera_dev = get_camera_dev()
			if camera_dev is not None:
				capture_window = find_second_window()
				if capture_window is not None:
					obs.create_split_scene(camera_dev, capture_window)
					sleep(1)

	except ObsError as e:
		flash("OBS: %s" % str(e))

	if message is not None:
		return progress_callback_response(message)
	else:
		return redirect(".")

@blueprint.route("/scenes/upload", methods=["POST"])
def page_scenes_upload():
	files = request.files.getlist("files")	 # Get the Werkzeug FileStorage object
	for file in files:
		# FIXME: Cyrillic characters are deleted!
		# FIXME: We need to ensure uniquiness
		save_as = os.path.join(current_app.config["CACHEDIR"], "upload-" + secure_filename(file.filename))
		file.save(save_as)
		obs.add_media_scene(os.path.basename(file.filename), file.mimetype.split("/")[0], save_as)
	return redirect(".")

