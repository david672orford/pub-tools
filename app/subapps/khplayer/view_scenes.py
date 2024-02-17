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
		scene_names = list(map(lambda scene: scene["sceneName"], reversed(obs.get_scene_list())))
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
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
	try:
		# Button press
		match request.form.get("action", "scene"):

			case "scene":
				scene = request.form.get("scene")
				obs.set_current_program_scene(scene)
	
			case "delete":
				scenes = request.form.getlist("del")
				try:
					obs.remove_scenes(scenes)
				except ObsError as e:
					async_flash(str(e))

			case "add-live":
				return redirect(".?action=add-live")

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

	except ObsError as e:
		async_flash(_("OBS: %s") % str(e))

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
	parsed_url = urlparse(url)
	q = parse_qs(parsed_url.query).keys()
	run_thread(lambda: page_scenes_add_url_worker(url))
	return progress_response(_("Loading dropped URL..."))

def page_scenes_add_url_worker(url):
	sleep(1)
	if meeting_loader.parse_video_url(url):
		load_video_url(None, url)
	else:
		load_webpage(None, url)

@blueprint.route("/scenes/add-html", methods=["POST"])
def page_scenes_add_html():
	html = request.form["add-html"]
	# FIXME: code missing
	print(html)
	return progress_response(_("Not implemented"), last_message=True)

def scene_event_handler(event):
	if event["eventType"] == "SceneListChanged":
		return
	print("%s %s" % (event["eventType"], json.dumps(event["eventData"], indent=2, ensure_ascii=False)))
	update = None
	with scene_event_handler.app.app_context():
		match event["eventType"]:
			case "SceneCreated":
				update = render_template("khplayer/scenes_event_created.html", event=event)
			case "SceneRemoved":
				update = render_template("khplayer/scenes_event_removed.html", event=event)
			case "SceneNameChanged":
				update = render_template("khplayer/scenes_event_rename.html", event=event)
			case "CurrentProgramSceneChanged":
				update = render_template("khplayer/scenes_event_program.html", event=event)
			case "CurrentPreviewSceneChanged":
				update = render_template("khplayer/scenes_event_preview.html", event=event)
	if update is not None:
		print("update:", update)
		turbo.push(update)

obs.subscribe("scenes", scene_event_handler)	

