from flask import current_app, Blueprint, render_template, request, redirect, flash
from werkzeug.utils import secure_filename
from time import sleep
import os, logging

from ...utils import progress_callback_response
from ...babel import gettext as _
from .views import blueprint, menu
from .utils import obs, ObsError
from .cameras import list_cameras
from .zoom import find_second_window

logger = logging.getLogger(__name__)

menu.append((_("Scenes"), "/scenes/"))

@blueprint.route("/scenes/")
def page_scenes():
	try:
		scene_names = list(map(lambda scene: scene["sceneName"], reversed(obs.get_scene_list())))
	except ObsError as e:
		flash("OBS: %s" % str(e))
		scene_names = []

	return render_template(
		"khplayer/scenes.html",
		cameras = list_cameras() if request.args.get("action") == "add-live" else None,
		scene_names = scene_names,
		top = ".."
		)

@blueprint.route("/scenes/submit", methods=["POST"])
def page_scenes_submit():
	logger.debug("scenes form: %s", request.form)
	message = None
	try:
		# Button press
		match request.form.get("action", "scene"):

			case "scene":
				scene = request.form.get("scene")
				obs.set_current_program_scene(scene)
				message = _("Scene switched to %s") % scene
	
			case "delete":
				for scene in request.form.getlist("del"):
					try:
						obs.remove_scene(scene)
					except ObsError as e:
						flash(str(e))
				sleep(1)

			case "add-live":
				return redirect(".?action=add-live")

			case "add-camera":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					obs.create_camera_scene(_("* Camera"), camera_dev)
					sleep(1)

			case "add-zoom":
				capture_window = find_second_window()
				if capture_window is not None:
					obs.create_zoom_scene(_("* Zoom"), capture_window)
					sleep(1)

			case "add-split":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					capture_window = find_second_window()
					if capture_window is not None:
						obs.create_split_scene(_("* Split Screen"), camera_dev, capture_window)
						sleep(1)

	except ObsError as e:
		flash(_("OBS: %s") % str(e))

	if message is not None:
		return progress_callback_response(message)
	else:
		return redirect(".")

# We tried combining this with the above, but it made things messier:
# * If no file is selected, you get a dummy file object with a mimetype of application/octet-stream
# * We need to provide an action value for file upload. We could do that with the button, but
#   with drag-and-drop it is more awkward. We would probably have to simulate a button click.
@blueprint.route("/scenes/upload", methods=["POST"])
def page_scenes_upload():
	files = request.files.getlist("files")	# Get the Werkzeug FileStorage object
	for file in files:
		major_mimetype = file.mimetype.split("/")[0]
		if major_mimetype not in ("video", "image"):
			flash(_("Unsupported media type: %s") % major_mimetype)
			continue
		# FIXME: Cyrillic characters are deleted!
		# FIXME: We need to ensure uniquiness
		save_as = os.path.join(current_app.config["CACHEDIR"], "upload-" + secure_filename(file.filename))
		file.save(save_as)
		obs.add_media_scene(os.path.basename(file.filename), major_mimetype, save_as)
	return redirect(".")

