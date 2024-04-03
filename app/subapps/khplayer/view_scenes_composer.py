from flask import current_app, request, session, render_template, redirect
from time import sleep
import logging

from .views import blueprint
from ...utils.babel import gettext as _
from ...utils.background import flash
from .utils.controllers import obs, ObsError
from .utils.cameras import list_cameras
from .utils.zoom import find_second_window

logger = logging.getLogger(__name__)

bounds_options = (
	(1280, 720, 0, 0),		# Fullscreen
	(638, 720, 0, 0),		# Left, Half
	(638, 720, 642, 0),		# Right, Half
	(640, 640, 0, 40),		# Left, Square
	(640, 640, 640, 40),	# Right, Square
	(640, 360, 0, 180),		# Left, Letterbox
	(640, 360, 640, 180),	# Right, Letterbox
	(240, 360, 0, 0),		# Portrait
	(240, 360, 1040, 360),	# Portrait
	)

@blueprint.route("/scenes/composer/<scene_uuid>/")
def page_scenes_composer(scene_uuid):
	scene_name = None
	scene_items = []

	try:
		scene_name = obs.get_scene_name(scene_uuid)

		for scene_item in obs.get_scene_item_list(scene_uuid):

			# FIXME: An ffmpeg_source which is not playing will have zero width
			# so we skip it to avoid a ZeroDivisionError exception in SceneItem
			if scene_item["sceneItemTransform"]["sourceWidth"] == 0:
				continue

			# We need each item scaled to bounds to do PTZ
			xform = scene_item["sceneItemTransform"]
			if xform["boundsType"] == "OBS_BOUNDS_NONE":
				xform["boundsType"] = "OBS_BOUNDS_SCALE_INNER"
				xform["boundsWidth"] = 1280
				xform["boundsHeight"] = 720
				obs.set_scene_item_transform(scene_uuid, scene_item["sceneItemId"], xform)

			scene_items.append(SceneItem(scene_item))

	except ObsError as e:
		flash(_("OBS: %s") % str(e))

	return render_template("khplayer/scenes_composer.html",
		scene_uuid = scene_uuid,
		scene_name = scene_name,
		scene_items = reversed(scene_items),
		cameras = list_cameras() if request.args.get("action") == "add-source" else None,
		remotes = current_app.config.get("REMOTES"),
		bounds_options = bounds_options,
		top = "../../../",
		)

class SceneItem: 
	def __init__(self, scene_item):
		logger.debug("SceneItem: %s", scene_item)
		self.id = scene_item["sceneItemId"]
		self.index = scene_item["sceneItemIndex"]
		self.name = scene_item["sourceName"]
		self.enabled = scene_item["sceneItemEnabled"]
		self.source_uuid = scene_item["sourceUuid"]
		xform = scene_item["sceneItemTransform"]
		self.width = xform["sourceWidth"]
		self.height = xform["sourceHeight"]
		self.bounds_width = xform["boundsWidth"]
		self.bounds_height = xform["boundsHeight"]
		self.position_x = xform["positionX"]
		self.position_y = xform["positionY"]

		x_total_crop = xform["cropLeft"] + xform["cropRight"]
		y_total_crop = xform["cropTop"] + xform["cropBottom"]

		# This positions of our X and Y sliders
		self.x = (xform["cropLeft"] * 100.0 / x_total_crop) if x_total_crop >= 1.0 else 50
		self.y = (xform["cropBottom"] * 100.0 / y_total_crop) if y_total_crop >= 1.0 else 50

		self.zoom = self.height / float(self.height - y_total_crop)

		self.thumbnail_url = obs.get_source_screenshot(scene_item["sourceUuid"])

@blueprint.route("/scenes/composer/<scene_uuid>/rename-scene", methods=["POST"])
def page_scenes_composer_rename_scene(scene_uuid):
	try:
		obs.set_scene_name(request.form["scene_name"])
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
	return redirect(".")

@blueprint.route("/scenes/composer/<scene_uuid>/action", methods=["POST"])
def page_scenes_composer_add_source(scene_uuid):
	try:
		action = request.form.get("action", "scene").split(":",1)
		match action[0]:

			case "add-camera":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					scene_item_id = obs.add_camera_input(scene_uuid, camera_dev)
	
			case "add-zoom":
				capture_window = find_second_window()
				if capture_window is not None:
					scene_item_id = obs.add_zoom_input(scene_uuid, capture_window)
					obs.scale_scene_item(scene_uuid, scene_item_id)

			case "add-remote":
				settings = current_app.config["REMOTES"][action[1]]
				scene_item_id = obs.add_remote_input(scene_uuid, settings)
				#obs.scale_scene_item(scene_uuid, scene_item_id)

			case "delete":
				obs.remove_scene_item(scene_uuid, int(request.form["scene_item_id"]))

			case "set-index":
				obs.set_scene_item_index(scene_uuid, int(request.form["scene_item_id"]), int(action[1]))

			case _:
				flash("Internal error: missing case: %s" % action[0])

	except ObsError as e:
		flash(_("OBS: %s") % str(e))

	sleep(1)
	return redirect(".")

@blueprint.route("/scenes/composer/<scene_uuid>/set-enabled", methods=["POST"])
def page_scenes_composer_enabled(scene_uuid):
	obs.set_scene_item_enabled(scene_uuid, request.json["id"], request.json["enabled"])
	return "OK"

@blueprint.route("/scenes/composer/<scene_uuid>/ptz", methods=["POST"])
def page_scenes_composer_ptz(scene_uuid):
	logger.debug("PTZ: %s", request.json)
	return ptz(scene_uuid=scene_uuid, **request.json)

def ptz(scene_uuid, id, bounds, new_bounds, dimensions, x, y, zoom, face_source_uuid):
	bounds_width, bounds_height, position_x, position_y = map(float, bounds.split(" "))
	width, height = map(float, dimensions.split(" "))

	if face_source_uuid:
		face = find_face(scene_uuid, id, face_source_uuid)
		if face:
			x, y, zoom = face

	pad = Padded(width, height, bounds_width, bounds_height)

	# How many pixels must be cut off in each dimension?
	# If zoom is 1.0, the answer will be zero.
	normalized_zoom = zoom * (pad.padded_height / height)
	x_total_crop = max(0, pad.padded_width - (pad.padded_width / normalized_zoom) - pad.width_padding)
	y_total_crop = max(0, pad.padded_height - (pad.padded_height / normalized_zoom) - pad.height_padding)
	logger.debug("total crops: %s %s", x_total_crop, y_total_crop)

	# x and y specify the percent of the cut off pixels which should be
	# taken from the left and bottom sides respectively.
	crop_left = x_total_crop * (x / 100.0)
	crop_bottom = y_total_crop * (y / 100.0)

	xform = {
		"cropLeft": crop_left, 
		"cropRight": (x_total_crop - crop_left),
		"cropTop": (y_total_crop - crop_bottom),
		"cropBottom": crop_bottom,
		}

	if new_bounds:
		xform.update({
			"boundsWidth": bounds_width,
			"boundsHeight": bounds_height,
			"positionX": position_x,
			"positionY": position_y,
			})

	obs.set_scene_item_transform(scene_uuid, id, xform)

	return {
		"x": x,
		"y": y,
		"zoom": zoom,
		}

class Padded:
	def __init__(self, width, height, bounds_width, bounds_height):

		# If we were to scale this image to the inner bounds (in OBS terminology)
		# one side may have black bars at top and bottom. Get the total
		# thickness of the top-bottom and left-right bars in the coordinate
		# space of the image.
		height_fill_scale = bounds_height / height
		self.width_padding = max(0, (bounds_width - (width * height_fill_scale)) / height_fill_scale)

		width_fill_scale = bounds_width / width
		self.height_padding = max(0, (bounds_height - (height * width_fill_scale)) / width_fill_scale)

		logger.debug("fill scales: %s, %s", width_fill_scale, height_fill_scale)
		logger.debug("paddings: %s, %s", self.width_padding, self.height_padding)

		# Dimensions of image if it were padded to teh same aspect ration as the bounds
		self.padded_width = width + self.width_padding
		self.padded_height = height + self.height_padding

# Face Detection
# See https://pypi.org/project/face-recognition/
def find_face(scene_uuid, id, source_uuid):
	backoff = 2.2

	from face_recognition import load_image_file, face_locations

	tempfile = obs.save_source_screenshot(source_uuid)
	image = load_image_file(tempfile)
	image_height, image_width = image.shape[:2]

	faces = face_locations(image)
	if len(faces) > 0:
		print("faces:", faces)
		top, right, bottom, left = faces[0]
		print("horizontal: %s -- %s" % (left, right))
		print("vertical: %s -- %s" % (top, bottom))

		face_width = right - left
		face_height = bottom - top
		print("face size:", face_width, face_height)

		face_x = (left + right) / 2
		face_y = (top + bottom) / 2
		print("face pos:", face_x, face_y)

		#x = face_x / image_width
		free_left = left
		free_right = image_width - right
		print("horizontal margins:", free_left, free_right)
		x = free_left / (free_left + free_right)

		#y = face_y / image_height
		free_top = top
		free_bottom = image_height - bottom
		y = free_top / (free_top + free_bottom)

		return (
			int(x * 100),									# X
			int((1.0 - y) * 100),							# Y (inverted)
			max(image_height / face_height / backoff, 1.0)	# Zoom
			)
	return None

