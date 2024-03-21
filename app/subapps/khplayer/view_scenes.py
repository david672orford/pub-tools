from flask import current_app, Blueprint, render_template, request, redirect
from time import sleep
from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os, re, json, logging

from ...utils.background import turbo, progress_callback, progress_response, run_thread, flash, async_flash
from ...utils.babel import gettext as _
from . import menu
from .views import blueprint
from .utils.controllers import obs, ObsError
from .utils.scenes import scene_name_prefixes, load_video_url, load_webpage
from .utils.cameras import list_cameras
from .utils.zoom import find_second_window
from .utils.controllers import meeting_loader

logger = logging.getLogger(__name__)

menu.append((_("Scenes"), "/scenes/"))

@blueprint.route("/scenes/")
def page_scenes():
	try:
		response = obs.get_scene_list()
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		response = {"scenes": []}

	try:
		for scene in response["scenes"]:
			if not "thumbnail_url" in scene:
				scene["thumbnail_url"] = get_scene_thumbnail(scene)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))

	return render_template(
		"khplayer/scenes.html",
		cameras = list_cameras() if request.args.get("action") == "add-scene" else None,
		scenes = response["scenes"],
		program_scene_uuid = response.get("currentProgramSceneUuid"),
		preview_scene_uuid = response.get("currentPreviewSceneUuid"),
		top = ".."
		)

def scenes_event_handler(event):
	if event["eventType"] == "SceneListChanged":
		return
	logger.debug("%s %s", event["eventType"], json.dumps(event["eventData"], indent=2, ensure_ascii=False))

	scene = event["eventData"]
	with blueprint.app.app_context():
		match event["eventType"]:
			case "SceneCreated":
				print("view_scenes:", scene)
				turbo.push(render_template("khplayer/scenes_event_created.html", scene=scene))
			case "SceneRemoved":
				turbo.push(render_template("khplayer/scenes_event_removed.html", scene=scene))
			case "SceneNameChanged":
				turbo.push(render_template("khplayer/scenes_event_rename.html", scene=scene))
			case "CurrentProgramSceneChanged":
				turbo.push(render_template("khplayer/scenes_event_changed.html",
					class_name = "program-scene",
					uuid = scene["sceneUuid"],
					))
			case "CurrentPreviewSceneChanged":
				turbo.push(render_template("khplayer/scenes_event_changed.html",
					class_name = "preview-scene",
					uuid = scene["sceneUuid"],
					))

obs.subscribe("Scenes", scenes_event_handler)

def scene_items_event_handler(event):
	logger.debug("%s %s", event["eventType"], json.dumps(event["eventData"], indent=2, ensure_ascii=False))
	scene = event["eventData"]
	scene["thumbnail_url"] = get_scene_thumbnail(scene)
	with blueprint.app.app_context():
		turbo.push(render_template("khplayer/scenes_event_thumbnail.html", scene=scene))

obs.subscribe("SceneItems", scene_items_event_handler)

def get_scene_thumbnail(scene):
	return obs.get_source_screenshot(scene["sceneUuid"])

@blueprint.route("/scenes/move-scene", methods=["POST"])
def page_scenes_move_scene():
	print(request.json)
	data = request.json
	obs.move_scene(data["uuid"], data["new_pos"])
	return ""

@blueprint.route("/scenes/submit", methods=["POST"])
def page_scenes_submit():
	logger.debug("scenes submit: %s", request.form)
	try:
		# Button press
		match request.form.get("action", "scene"):

			case "scene":
				scene = request.form.get("scene")
				if obs.get_current_preview_scene()["sceneUuid"] is not None:
					obs.set_current_preview_scene(scene)
				else:
					obs.set_current_program_scene(scene)

			case "delete":
				scenes = request.form.getlist("del")
				try:
					obs.remove_scenes(scenes)
				except ObsError as e:
					async_flash(str(e))

			case "add-scene":
				return redirect(".?action=add-scene")

			case "add-camera":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					obs.create_camera_scene(_("* Camera"), camera_dev)

			case "add-zoom":
				capture_window = find_second_window()
				if capture_window is not None:
					obs.create_zoom_scene(_("* Zoom"), capture_window)

			case "add-split":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					capture_window = find_second_window()
					if capture_window is not None:
						obs.create_split_scene(_("* Split Screen"), camera_dev, capture_window)

			case "add-empty":
				obs.create_scene(_("* New Scene"), make_unique=True)

			case "composer":
				scene = obs.get_current_preview_scene()
				if scene["sceneUuid"] is None:
					scene = obs.get_current_program_scene()
				print("composer scene:", scene)
				return redirect(f"composer/{scene['sceneUuid']}/")

			case _:
				flash("Internal error: missing case")
				return redirect(".")

	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))

	# FIXME: It seems if we return before the change is rendered, it may not be.
	sleep(1)

	return turbo.stream("")

# We tried combining this with the above, but it made things messier:
# * If no file is selected, you get a dummy file object with a mimetype of application/octet-stream
# * We need to provide an action value for file upload. We could do that with the button, but
#   with drag-and-drop it is more awkward. We would probably have to simulate a button click.
@blueprint.route("/scenes/upload", methods=["POST"])
def page_scenes_upload():
	files = request.files.getlist("files")				# Get the Werkzeug FileStorage object
	datestamp = datetime.now().strftime("%Y%m%d%H%M%S")
	i = 1
	for file in files:
		progress_callback(_("Loading local file \"%s\" (%s)...") % (file.filename, file.mimetype))

		major_mimetype = file.mimetype.split("/")[0]
		scene_name_prefix = scene_name_prefixes.get(major_mimetype)
		if scene_name_prefix is None:
			progress_callback(_("Unsupported media type: %s") % file.mimetype, cssclass="error")
			continue

		# Save to file with name in format user-YYYYMMDDHHMMSS-X.ext
		m = re.search(r"(\.[a-zA-Z0-9]+)$", file.filename)
		ext = m.group(1) if m else ""
		save_as = os.path.join(
			current_app.config["MEDIA_CACHEDIR"],
			"user-%s-%d%s" % (datestamp, i, ext),
			)
		file.save(save_as)

		try:
			obs.add_media_scene(
				scene_name_prefix + " " + os.path.basename(file.filename),
				major_mimetype,
				save_as
				)
		except ObsError as e:
			async_flash(_("OBS: %s") % str(e))

		i += 1
	return progress_response(_("Done."), last_message=True)

# When a URL is dropped onto the scene list
@blueprint.route("/scenes/add-url", methods=["POST"])
def page_scenes_add_url():
	url = request.form["add-url"]
	def background_loader():
		sleep(1)
		if meeting_loader.parse_video_url(url):
			load_video_url(None, url)
		else:
			load_webpage(None, url)
	run_thread(background_loader)
	return progress_response(_("Loading dropped URL..."), cssclass="heading")

@blueprint.route("/scenes/add-html", methods=["POST"])
def page_scenes_add_html():
	html = request.form["add-html"]
	# FIXME: code missing
	print(html)
	return progress_response(_("Not implemented"), last_message=True)

