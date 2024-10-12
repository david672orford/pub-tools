from flask import current_app, Blueprint, render_template, request, redirect
from time import sleep
from urllib.parse import urlparse, parse_qs
import os, re, json, logging

from ...utils.background import turbo, progress_callback, progress_response, run_thread, flash, async_flash
from ...utils.babel import gettext as _
from ...utils.media_cache import make_media_cachefile_name
from . import menu
from .views import blueprint
from .utils.controllers import obs, ObsError
from .utils.scenes import scene_name_prefixes, load_video_url, load_image_url, load_webpage, load_text, load_meeting_media_item
from .utils.cameras import list_cameras
from .utils.zoom import find_second_window
from .utils.controllers import meeting_loader
from .utils.html_extractor import HTML

logger = logging.getLogger(__name__)

menu.append((_("Scenes"), "/scenes/"))

def get_scenes_with_thumbnails():
	try:
		scenes = obs.get_scene_list()
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
		scenes = {"scenes": []}

	try:
		for scene in scenes["scenes"]:
			if not "thumbnail_url" in scene:
				scene["thumbnail_url"] = get_scene_thumbnail(scene)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))

	return scenes

def get_scene_thumbnail(scene):
	return obs.get_source_screenshot(scene["sceneUuid"])

@blueprint.route("/scenes/")
def page_scenes():
	scenes = get_scenes_with_thumbnails()
	return render_template(
		"khplayer/scenes.html",
		scenes = scenes["scenes"],
		program_scene_uuid = scenes.get("currentProgramSceneUuid"),
		preview_scene_uuid = scenes.get("currentPreviewSceneUuid"),
		cameras = list_cameras() if request.args.get("action") == "add-scene" else None,
		remotes = current_app.config.get("VIDEO_REMOTES"),
		top = ".."
		)

# Update the scenes list when scenes are added, removed, renamed
def scenes_event_handler(event):
	if event["eventType"] == "SceneListChanged":
		return
	logger.debug("%s %s", event["eventType"], json.dumps(event["eventData"], indent=2, ensure_ascii=False))

	data = event["eventData"]
	with blueprint.app.app_context():
		match event["eventType"]:
			case "CurrentSceneCollectionChanged":
				scenes = get_scenes_with_thumbnails()
				turbo.push(render_template("khplayer/scenes_event_reload.html",
					scenes = scenes["scenes"],
					program_scene_uuid = scenes.get("currentProgramSceneUuid"),
					preview_scene_uuid = scenes.get("currentPreviewSceneUuid"),
					))
			case "SceneCreated":
				turbo.push(render_template("khplayer/scenes_event_created.html", scene=data))
			case "SceneRemoved":
				turbo.push(render_template("khplayer/scenes_event_removed.html", scene=data))
			case "SceneNameChanged":
				turbo.push(render_template("khplayer/scenes_event_rename.html", scene=data))
			case "CurrentProgramSceneChanged":
				turbo.push(render_template("khplayer/scenes_event_changed.html",
					class_name = "program-scene",
					uuid = data["sceneUuid"],
					))
			case "CurrentPreviewSceneChanged":
				turbo.push(render_template("khplayer/scenes_event_changed.html",
					class_name = "preview-scene",
					uuid = data["sceneUuid"],
					))
			case "StudioModeStateChanged":
				if not data["studioModeEnabled"]:
					turbo.push(render_template("khplayer/scenes_event_changed.html",
						class_name = "preview-scene",
						uuid = None,
						))

obs.subscribe("Config", scenes_event_handler)		# scene collection?
obs.subscribe("Scenes", scenes_event_handler)
obs.subscribe("Ui", scenes_event_handler)			# studio mode

# Reload thumbnail when scene items are added, removed, hidden, revealed
def scene_items_event_handler(event):
	logger.debug("%s %s", event["eventType"], json.dumps(event["eventData"], indent=2, ensure_ascii=False))
	scene = event["eventData"]
	scene["thumbnail_url"] = get_scene_thumbnail(scene)
	with blueprint.app.app_context():
		turbo.push(render_template("khplayer/scenes_event_thumbnail.html", scene=scene))

obs.subscribe("SceneItems", scene_items_event_handler)

@blueprint.route("/scenes/refresh-thumbnail", methods=["POST"])
def page_scenes_refresh_thumbnail():
	uuid = request.json["uuid"]
	for scene in get_scenes_with_thumbnails()["scenes"]:
		if scene["sceneUuid"] == uuid:
			scene["thumbnail_url"] = get_scene_thumbnail(scene)
			turbo.push(render_template("khplayer/scenes_event_thumbnail.html", scene=scene))
			break
	return ""

@blueprint.route("/scenes/move-scene", methods=["POST"])
def page_scenes_move_scene():
	logger.debug("Move scene: %s", request.json)
	data = request.json
	try:
		obs.move_scene(data["uuid"], data["new_pos"])
	except KeyError:
		logger.error("Attempt to move non-existent scene: %s", data["uuid"])
	return ""

@blueprint.route("/scenes/submit", methods=["POST"])
def page_scenes_submit():
	logger.debug("scenes submit: %s", request.form)
	try:
		# Button press
		action = request.form.get("action", "scene").split(":",1)
		match action[0]:

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

			case "add-camera+zoom":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					capture_window = find_second_window()
					if capture_window is not None:
						obs.create_split_scene(_("* Camera+Zoom"), camera_dev, capture_window)

			case "add-remote":
				settings = current_app.config["VIDEO_REMOTES"][action[1]]
				obs.create_remote_scene("* %s" % action[1], settings)

			case "add-empty":
				obs.create_scene(_("* New Scene"), make_unique=True)

			case "composer":
				scene = obs.get_current_preview_scene()
				if scene["sceneUuid"] is None:
					scene = obs.get_current_program_scene()
				return redirect(f"composer/{scene['sceneUuid']}/")

			case _:
				flash("Internal error: missing case: %s" % action[0])
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
	i = 1
	for file in files:
		progress_callback(_("Loading local file \"%s\" (%s)...") % (file.filename, file.mimetype), cssclass="heading")

		major_mimetype = file.mimetype.split("/")[0]
		scene_name_prefix = scene_name_prefixes.get(major_mimetype)
		if scene_name_prefix is None:
			progress_callback(_("Unsupported media type: %s") % file.mimetype, cssclass="error")
			continue

		save_as = make_media_cachefile_name(file.filename)
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

	return progress_response(_("✔ File has been loaded."), last_message=True, cssclass="success")

# When an HTML element from a web browser is dropped onto the scene list
@blueprint.route("/scenes/add-html", methods=["POST"])
def page_scenes_add_html():
	html_text = request.form["add-html"]
	doc = HTML(html_text)

	if doc.doc.tag == "a":
		href = doc.doc.attrib.get("href")
		if href:
			pub = meeting_loader.get_pub_from_a_tag(doc.doc)
			print("pub:", pub)
			if pub is not None:
				def background_loader():
					sleep(1)
					load_meeting_media_item(pub)
					progress_callback(_("✔ Publication has been loaded."), last_message=True, cssclass="success")
				run_thread(background_loader)
				return progress_response(_("Loading dropped publication..."), cssclass="heading")
			return add_url(href)

	elif doc.doc.tag == "img":
		title = doc.doc.attrib.get("alt", "Image")
		url = doc.doc.attrib.get("src")
		def background_loader():
			sleep(1)
			load_image_url(title, url)
		run_thread(background_loader)
		return progress_response(_("Loading image..."))

	# If we get here, presume the intent was to create a text slide.
	print("Before:", doc.pretty())
	doc.cleanup()
	print("After:", doc.pretty())
	plain_text = doc.text_content()
	return load_text("Text", plain_text)

# When a URL is dropped onto the scene list
@blueprint.route("/scenes/add-url", methods=["POST"])
def page_scenes_add_url():
	return add_url(request.form["add-url"])

def add_url(url):
	def background_loader():
		sleep(1)
		if meeting_loader.parse_video_url(url):
			load_video_url(None, url)
		else:
			load_webpage(None, url)
	run_thread(background_loader)
	return progress_response(_("Loading dropped URL..."), cssclass="heading")

