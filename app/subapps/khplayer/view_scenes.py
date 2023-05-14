from flask import current_app, Blueprint, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
from time import sleep
import os, logging

from ...utils import progress_callback_response
from .views import blueprint, menu
from .utils import obs, ObsError

logger = logging.getLogger(__name__)

menu.append(("Scenes", "/scenes/"))

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
	logger.info("scenes action: %s %s", action, scene)

	try:
		if scene is not None:
			obs.set_current_program_scene(scene)
			message = "Scene switched to %s" % scene
	
		elif action == "delete":
			for scene in request.form.getlist("del"):
				try:
					obs.remove_scene(scene)
				except ObsError as e:
					flash(str(e))
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

