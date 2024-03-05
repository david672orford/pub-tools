from flask import request, session, render_template, redirect
import logging

from .views import blueprint
from ...utils.babel import gettext as _
from ...utils.background import flash
from .utils.controllers import obs, ObsError

logger = logging.getLogger(__name__)

@blueprint.route("/scenes/composer/")
def page_scene_composer():
	scene_uuid = None
	scene_items = []
	try:
		scene_uuid = obs.get_current_program_scene()["sceneUuid"]
		for scene_item in obs.get_scene_item_list(scene_uuid):
			# FIXME: An ffmpeg_source which is not playing will have no width and will
			# cause a ZeroDivisionError exception, so we skip it for now.
			if scene_item["sceneItemTransform"]["sourceWidth"] == 0:
				continue
			if scene_item["sceneItemTransform"]["boundsType"] == "OBS_BOUNDS_NONE":
				obs.set_scene_item_transform(scene_uuid, scene_item["sceneItemId"], {
					"boundsType": "OBS_BOUNDS_SCALE_INNER",
					"boundsWidth": 1280,
					"boundsHeight": 720,
					})
			scene_items.append(SceneItem(scene_uuid, scene_item))
		scene_items = reversed(scene_items)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
	return render_template("khplayer/scene_composer.html", scene_uuid=scene_uuid, scene_items=scene_items, top="../..")

class SceneItem: 
	def __init__(self, scene_uuid, scene_item):
		print(scene_item)
		self.scene_uuid = scene_uuid
		self.id = scene_item["sceneItemId"]
		self.index = scene_item["sceneItemIndex"]
		self.name = scene_item["sourceName"]
		xform = scene_item["sceneItemTransform"]
		self.width = xform["sourceWidth"]
		self.height = xform["sourceHeight"]
		self.bounds_width = xform["boundsWidth"]
		self.bounds_height = xform["boundsHeight"]
		self.position_x = xform["positionX"]
		self.position_y = xform["positionY"]

		x_total_crop = xform["cropLeft"] + xform["cropRight"]
		y_total_crop = xform["cropTop"] + xform["cropBottom"]
		self.x = (xform["cropLeft"] * 100.0 / x_total_crop) if x_total_crop >= 1.0 else 50
		self.y = (xform["cropBottom"] * 100.0 / y_total_crop) if y_total_crop >= 1.0 else 50
		x_zoom = self.width / float(self.width - x_total_crop)
		y_zoom = self.height / float(self.height - y_total_crop)
		print("recovered zooms:", x_zoom, y_zoom)
		self.zoom = max(x_zoom, y_zoom)

@blueprint.route("/scenes/composer/ptz", methods=["POST"])
def page_scene_composer_ptz():
	print(request.json)
	ptz(**request.json)
	return "OK"

def ptz(scene_uuid, id, bounds, new_bounds, dimensions, x, y, zoom):

	bounds_width, bounds_height, position_x, position_y = map(float, bounds.split(" "))
	width, height = map(float, dimensions.split(" "))

	# If we scale the image to (in OBS terminology) the inner bounds
	# one side may have black bars at top and bottom. Get the total
	# thickness of the top-bottom and left-right bars.
	height_fill_scale = bounds_height / height
	width_padding = max(0, (bounds_width - (width * height_fill_scale)) / height_fill_scale)
	width_fill_scale = bounds_width / width
	height_padding = max(0, (bounds_height - (height * width_fill_scale)) / width_fill_scale)
	print("paddings:", width_padding, height_padding)

	width += width_padding
	height += height_padding

	# How many pixels must be cut off in each dimension?
	# If zoom is 1.0, the answer will be zero.
	x_total_crop = max(0, width - (width / zoom) - width_padding)
	y_total_crop = max(0, height - (height / zoom) - height_padding)
	print("total crops:", x_total_crop, y_total_crop)

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

