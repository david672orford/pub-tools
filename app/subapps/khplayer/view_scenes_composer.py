import os.path

from flask import current_app, request, session, render_template, redirect
from time import sleep
import logging

from .views import blueprint
from ...utils.babel import gettext as _
from ...utils.background import flash
from .utils.controllers import obs, ObsError
from .utils.cameras import list_cameras
from .utils.zoom import zoom_tracker_loaded, find_second_window

logger = logging.getLogger(__name__)

bounds_options = (
	(1280, 720, 0, 0),		# Fullscreen
	(640, 720, 0, 0),		# Left half of screen
	(640, 720, 640, 0),		# Right half of screen
	(640, 640, 0, 40),		# Left, square
	(640, 640, 640, 40),	# Right, square
	(640, 480, 0, 120),		# Left, 4:3
	(640, 480, 640, 120),	# Right, 4:3
	(640, 360, 0, 180),		# Left, 16:9
	(640, 360, 640, 180),	# Right, 16:9
	#(240, 360, 0, 0),		# Portrait
	#(240, 360, 1040, 360),	# Portrait
	(320, 360, 0, 0),		# Portrait top-left
	(320, 360, 960, 360),	# Portrait bottom-right
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

		# The positions of our X and Y sliders
		self.x = (xform["cropLeft"] * 100.0 / x_total_crop) if x_total_crop >= 1.0 else 50
		self.y = (xform["cropBottom"] * 100.0 / y_total_crop) if y_total_crop >= 1.0 else 50

		self.zoom = self.height / float(self.height - y_total_crop)

		self.thumbnail_url = obs.get_source_screenshot(scene_item["sourceUuid"])

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

			# In order to do pseudo-PTZ we need to first make sure each item is scaled to bounds.
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
		remotes = current_app.config.get("VIDEO_REMOTES"),
		bounds_options = bounds_options,
		top = "../../../",
		)

@blueprint.route("/scenes/composer/<scene_uuid>/action", methods=["POST"])
def page_scenes_composer_add_source(scene_uuid):
	try:
		action = request.form.get("action", "scene").split(":",1)
		match action[0]:

			case "rename-scene":
				obs.set_scene_name(scene_uuid, request.form["scene_name"])

			case "delete":
				obs.remove_scene_item(scene_uuid, int(request.form["scene_item_id"]))

			case "set-index":
				obs.set_scene_item_index(scene_uuid, int(request.form["scene_item_id"]), int(action[1]))

			case "add-camera":
				camera_dev = request.form.get("camera")
				if camera_dev is not None:
					obs.add_camera_source(scene_uuid, camera_dev)

			case "add-zoom":
				if zoom_tracker_loaded():
					obs.add_existing_source(scene_uuid, f"Zoom Participant {action[1]}")
				elif action[1] == "0":
					capture_window = find_second_window()
					if capture_window is not None:
						scene_item_id = obs.add_capture_source(scene_uuid, capture_window)
						obs.scale_scene_item(scene_uuid, scene_item_id)

			case "add-remote":
				settings = current_app.config["VIDEO_REMOTES"][action[1]]
				obs.add_remote_source(scene_uuid, settings)

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

	# Where would we have to pad the image and by how much to match the aspect ratio of the bound?
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

# Figure out how well a width*height image would fit into a bounds_width*bounds_height space.
# Computed:
# width_padding -- Total width of black bars at top and bottom (0 if none)
# height_padding -- Total height of black bars at top and bottom (0 if none)
# padded_width -- Width after any black bars are added
# padded_height -- Height after any black bars are added
# All dimensions are in terms of image coordinate space units, not the bounds space.
class Padded:
	def __init__(self, width, height, bounds_width, bounds_height):

		# If we were to scale this image to the inner bounds (which in OBS
		# terminology means to make it as large as possible while preserving
		# the aspect ration and not cropping it at all) one side may have
		# black bars at top and bottom. Get the total thickness of the
		# top-bottom and left-right bars in the coordinate space of the image.
		height_fill_scale = bounds_height / height
		self.width_padding = max(0, (bounds_width - (width * height_fill_scale)) / height_fill_scale)

		width_fill_scale = bounds_width / width
		self.height_padding = max(0, (bounds_height - (height * width_fill_scale)) / width_fill_scale)

		logger.debug("fill scales: %s, %s", width_fill_scale, height_fill_scale)
		logger.debug("paddings: %s, %s", self.width_padding, self.height_padding)

		# Dimensions of image if it were padded to the same aspect ration as the bounds
		self.padded_width = width + self.width_padding
		self.padded_height = height + self.height_padding

# Face Detection
# Takes a snapshot of the indicated scene, finds the face, and computes
# and returns a view box for the speaker.
#
# This uses:
#   https://pypi.org/project/face-recognition/
# The initial experimental code was more ambitious and may be of value later:
#   https://github.com/david672orford/pub-tools/blob/v0.8/app/subapps/khplayer/cli_obs.py
# There you can find:
#  * Alternative implementation using Batch-Face
#  * Attempts to infer a head-and-shoulders box from the face bbox
#  * Smooth panning and zooming of the OBS transform to the selected crop box
def find_face(scene_uuid, id, source_uuid):
	backoff = 2.2

	from face_recognition import load_image_file, face_locations

	# Take a screenshot from the camera
	tempfile = os.path.join(current_app.instance_path, "face.jpg")
	obs.save_source_screenshot(source_uuid, tempfile)

	# Load screenshot into face recognizer
	image = load_image_file(tempfile)
	image_height, image_width = image.shape[:2]

	faces = face_locations(image)
	if len(faces) > 0:
		print("faces:", faces)
		top, right, bottom, left = faces[0]
		print(f"horizontal extent: {left} -- {right}")
		print(f"vertical extent: {top} -- {bottom}")

		face_width = right - left
		face_height = bottom - top
		print("face dimensions:", face_width, face_height)

		face_x = (left + right) / 2
		face_y = (top + bottom) / 2
		print("face center pos:", face_x, face_y)

		free_left = left
		free_right = image_width - right
		print("horizontal distance to image edges:", free_left, free_right)
		x = free_left / (free_left + free_right)

		free_top = top
		free_bottom = image_height - bottom
		y = free_top / (free_top + free_bottom)

		return (
			int(x * 100),									# X
			int((1.0 - y) * 100),							# Y (inverted)
			max(image_height / face_height / backoff, 1.0)	# Zoom
			)
	return None
