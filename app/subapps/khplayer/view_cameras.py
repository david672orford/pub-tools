from flask import request, session, render_template, redirect
import logging

from . import menu
from .views import blueprint
from ...utils.babel import gettext as _
from ...utils.background import flash
from .utils.controllers import obs, ObsError

logger = logging.getLogger(__name__)

menu.append((_("Cameras"), "/cameras/"))

@blueprint.route("/cameras/")
def page_cameras():
	cameras = []
	try:
		scene_uuid = obs.get_current_program_scene()["sceneUuid"]
		for scene_item in obs.get_scene_item_list(scene_uuid):
			# FIXME: An ffmpeg_source which is not playing will have no width and will
			# cause a ZeroDivisionError exception, so we slip it for now.
			if scene_item["sceneItemTransform"]["sourceWidth"] == 0:
				continue
			if scene_item["sceneItemTransform"]["boundsType"] == "OBS_BOUNDS_NONE":
				obs.set_scene_item_transform(scene_uuid, scene_item["sceneItemId"], {
					"boundsType": "OBS_BOUNDS_SCALE_INNER",
					"boundsWidth": 1280,
					"boundsHeight": 720,
					})
			cameras.append(Camera(scene_uuid, scene_item))
		cameras = reversed(cameras)
	except ObsError as e:
		flash(_("OBS: %s") % str(e))
	return render_template("khplayer/cameras.html", scene_uuid=scene_uuid, cameras=cameras, top="..")

class Camera:
	def __init__(self, scene_uuid, scene_item):
		print(scene_item)
		self.scene_uuid = scene_uuid
		self.id = scene_item["sceneItemId"]
		self.index = scene_item["sceneItemIndex"]
		self.name = scene_item["sourceName"]
		xform = scene_item["sceneItemTransform"]
		self.width = xform["sourceWidth"]
		self.height = xform["sourceHeight"]

		x_total_crop = xform["cropLeft"] + xform["cropRight"]
		y_total_crop = xform["cropTop"] + xform["cropBottom"]
		self.x = (xform["cropLeft"] * 100.0 / x_total_crop) if x_total_crop >= 1.0 else 50
		self.y = (xform["cropBottom"] * 100.0 / y_total_crop) if y_total_crop >= 1.0 else 50
		x_zoom = self.width / float(self.width - x_total_crop)
		y_zoom = self.height / float(self.height - y_total_crop)
		print(x_zoom, y_zoom)
		self.zoom = min(x_zoom, y_zoom)

@blueprint.route("/cameras/ptz", methods=["POST"])
def page_cameras_ptz():
	def ptz(scene_uuid, id, width, height, x, y, zoom):

		# How many pixels must be cut off in each dimension?
		# Of zoom is 1.0, the answer will be zero.
		x_total_crop = width - (width / zoom)
		y_total_crop = height - (height / zoom)

		# x and y specify the percent of the cut off pixels which should be
		# taken from the left and bottom sides respectively.
		crop_left = x_total_crop * (x / 100.0)
		crop_bottom = y_total_crop * (y / 100.0)

		obs.set_scene_item_transform(scene_uuid, id, {
			"cropLeft": crop_left, 
			"cropRight": (x_total_crop - crop_left),
			"cropTop": (y_total_crop - crop_bottom),
			"cropBottom": crop_bottom,
			})

	print(request.json)
	ptz(**request.json)

	return "OK"

