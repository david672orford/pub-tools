from flask import current_app, Blueprint, render_template, request, redirect
from time import sleep
from urllib.parse import urlparse, parse_qs, unquote
import os, re, json, logging

from ...utils.background import turbo, progress_callback, progress_response, \
	run_thread, flash, async_flash
from ...utils.babel import gettext as _
from ...utils.media_cache import make_media_cachefile_name
from . import menu
from .views import blueprint
from .utils.controllers import obs, ObsError
from .utils.scenes import scene_name_prefixes, load_video_url, load_image_url, \
	load_webpage, load_text, load_meeting_media_item, load_media_file
from .utils.cameras import list_cameras
from .utils.zoom import find_second_window
from .utils.controllers import meeting_loader
from .utils.html_extractor import HTML

logger = logging.getLogger(__name__)

menu.append((_("Scenes"), "/scenes/"))

#=============================================================================
# Display the scene list and keep it up-to-date
#=============================================================================

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

#=============================================================================
# User interaction with the scene list
#=============================================================================

# Called when mouse hovers over a scene thumbnail
@blueprint.route("/scenes/refresh-thumbnail", methods=["POST"])
def page_scenes_refresh_thumbnail():
	uuid = request.json["uuid"]
	for scene in get_scenes_with_thumbnails()["scenes"]:
		if scene["sceneUuid"] == uuid:
			scene["thumbnail_url"] = get_scene_thumbnail(scene)
			turbo.push(render_template("khplayer/scenes_event_thumbnail.html", scene=scene))
			break
	return ""

# Called when a user drags and drops to scene in a different position
@blueprint.route("/scenes/move-scene", methods=["POST"])
def page_scenes_move_scene():
	logger.debug("Move scene: %s", request.json)
	data = request.json
	try:
		obs.move_scene(data["uuid"], data["new_pos"])
	except KeyError:
		logger.error("Attempt to move non-existent scene: %s", data["uuid"])
	return ""

# Called when a button is pressed in the scene list
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

# Called when the user uploads a file to the scene list
#
# We tried combining this with the button-press handler above, but it
# made things messier:
# * When no file is selected, we got a dummy file object with a mimetype
#   of application/octet-stream
# * We needed to provide an action value for file upload. We could do that
#   with the button, but with drag-and-drop it is more awkward. We would
#   probably have to simulate a button click.
#
@blueprint.route("/scenes/upload", methods=["POST"])
def page_scenes_upload():
	files = request.files.getlist("files")				# Get the Werkzeug FileStorage object
	for file in files:
		progress_callback(_("Loading local file \"%s\" (%s)...") % (file.filename, file.mimetype), cssclass="heading")
		if file.mimetype.split("/")[0] not in scene_name_prefixes:
			progress_callback(_("Unsupported file type: \"%s\" (%s)") % (file.filename, file.mimetype), cssclass="error")
			continue
		save_as = make_media_cachefile_name(file.filename, file.mimetype)
		file.save(save_as)
		load_media_file(file.filename, save_as, file.mimetype, close=False)
	return progress_response(_("✔ All files have been loaded."), last_message=True, cssclass="success")

# Called when a bare URL is dropped onto the scene list
@blueprint.route("/scenes/add-url", methods=["POST"])
def page_scenes_add_url():
	return add_url(request.form["add-url"])

def add_url(url):
	def background_loader():
		sleep(1)

		url_obj = urlparse(url)
		if url_obj.hostname == "www.jw.org":

			# Share URL or Featured Video URL
			if meeting_loader.get_video_metadata(url):
				load_video_url(None, url)
				return

			# FIXME: We shouldn't need this
			# Featured video URL
			if (m := re.match(r"[^/]+/mediaitems/FeaturedLibraryVideos/([^/]+)$", url_obj.fragment)):
				media_url = "https://www.jw.org/finder?lank=" + m.group(1)
				load_video_url(None, media_url)
				return

		else:
			progress_callback(_("Fetching headers of \"%s\"...") % unquote(url))
			# HEAD times out on JW.ORG, so excluded
			response = meeting_loader.head(url)
			mimetype = response.headers.get("Content-Type").split(";")[0]
			if mimetype.split("/")[0] in scene_name_prefixes:
				filename = os.path.basename(unquote(urlparse(url).path))
				save_as = make_media_cachefile_name(filename, mimetype)
				meeting_loader.download_media(url, cachefile=save_as, callback=progress_callback)
				load_media_file(filename, save_as, mimetype, close=True)
				return

		# Anything else gets displayed in a webview.
		# We use None for scene_name so it will be taken from <title>.
		load_webpage(None, url)

	run_thread(background_loader)
	return progress_response(_("Loading dropped URL..."), cssclass="heading")

# Called when an HTML element from a web browser is dropped onto the scene list
@blueprint.route("/scenes/add-html", methods=["POST"])
def page_scenes_add_html():
	html_text = request.form["add-html"]
	doc = HTML(html_text)

	# A URL wrapped in an <a> tag
	if doc.doc.tag == "a":
		href = doc.doc.attrib.get("href")
		if href:
			# If we recognize the attributes of an <a> tag from JW.ORG which links to a media item,
			if (pub := meeting_loader.get_pub_from_a_tag(doc.doc, dnd=True)) is not None:
				def background_loader():
					sleep(1)
					load_meeting_media_item(pub)
					progress_callback(_("✔ Publication has been loaded."), last_message=True, cssclass="success")
				run_thread(background_loader)
				return progress_response(_("Loading dropped publication..."), cssclass="heading")

			# Otherwise, chain to the bare URL handler
			return add_url(href)

	# A URL wrapped in an <img> tag
	elif doc.doc.tag == "img":
		title = doc.doc.attrib.get("alt", "Image")
		url = doc.doc.attrib.get("src")
		def background_loader():
			sleep(1)
			load_image_url(title, url)
		run_thread(background_loader)
		return progress_response(_("Loading dropped image..."))

	# If we get here, presume the intent was to create a text slide.
	print("Before:", doc.pretty())
	doc.cleanup()
	print("After:", doc.pretty())
	plain_text = doc.text_content()
	return load_text("Text", plain_text)

# Called when a piece of plain text is dropped onto the scene list
@blueprint.route("/scenes/add-text", methods=["POST"])
def page_scenes_add_text():
	text = request.form["add-text"]
	if text.startswith("https://"):
		return add_url(text)
	return load_text("Text", text)

