"""
CLI for the Zoom tracker
"""

import os.path
from time import time, sleep

from flask import current_app
from flask.cli import AppGroup
import click
from PIL import Image

from .utils.controllers import obs, ObsError
from .utils.zoom_tracker import ZoomBoxFinder

cli_zoom = AppGroup("zoom", help="Zoom scene control")

@cli_zoom.command("test")
@click.argument("filename")
def cmd_zoom_test(filename):
	"""Test the Zoom tracker on an image"""

	finder = ZoomBoxFinder()
	img = Image.open(filename)
	finder.load_image(img)

	print("Gallery:", finder.gallery)
	finder.draw_box(finder.gallery)

	print("Speaker size:", finder.speaker.width, finder.speaker.height)
	finder.draw_box(finder.speaker)

	print("Speaker index:", finder.speaker_indexes[0])

	for crop in finder.layout:
		finder.draw_box(crop)

	finder.img.show()

@cli_zoom.command("track")
def cmd_zoom_track():
	"""Run the Zoom tracker through OBS-Websocket"""
	zoom_input_name = "Zoom Capture"
	filename = os.path.join(current_app.instance_path, zoom_input_name + ".png")

	zoom_input_uuid = obs.get_input_uuid(zoom_input_name)
	assert zoom_input_uuid is not None, "%s not found" % zoom_input_name

	zoom_scenes = (
		ZoomCropper("* Zoom Speaker", zoom_input_name, zoom_input_uuid),
		ZoomCropper("* Zoom 1", zoom_input_name, zoom_input_uuid),
		ZoomCropper("* Zoom 2", zoom_input_name, zoom_input_uuid),
		)

	finder = ZoomBoxFinder()

	while True:
		try:
			print("Getting snapshot of Zoom window...")
			start = time()
			response = obs.request("SaveSourceScreenshot", {
				"sourceUuid": zoom_input_uuid,
				"imageFormat": "png",
				"imageFilePath": filename,
				"imageCompressionQuality": 50,
				})
			print("Elapsed time: %dms" % int((time() - start) * 1000))

			# Load image from file and drop the transparency
			img = Image.open(filename).convert("RGB")

			# Load into our box finder and try to figure out the layout
			finder.load_image(img)

			# Adjust the cropping on all of the Zoom scenes
			finder.do_cropping(zoom_scenes)

		except ObsError as e:
			print("OBS Error:", e)

		print()
		sleep(3)

class ZoomCropper:
	"""
	We crop pieces out of the Zoom window by creating a series of scenes each
	of which has a single item which is the Zoom capture input. We do the
	cropping by setting the transform. This class finds or creates the
	pieces we need and warps them up into a neat little package.
	There is an OBS-API version of this in khplayer-zoom-tracker.py.
	"""

	def __init__(self, scene_name, zoom_input_name, zoom_input_uuid):
		self.prev_crop = None

		self.scene_uuid = obs.get_scene_uuid(scene_name)
		if self.scene_uuid is None:
			self.scene_uuid = obs.create_scene(scene_name)["sceneUuid"]

		self.scene_item_id = obs.get_scene_item_id(self.scene_uuid, zoom_input_name)
		if self.scene_item_id is None:
			self.scene_item_id = obs.create_scene_item(scene_uuid=self.scene_uuid, source_uuid=zoom_input_uuid)

	def set_crop(self, crop):
		if crop != self.prev_crop:
			if crop is False:
				obs.set_scene_item_enabled(self.scene_uuid, self.scene_item_id, False)
			else:
				if self.prev_crop is False:
					obs.set_scene_item_enabled(self.scene_uuid, self.scene_item_id, True)
				obs.scale_scene_item(self.scene_uuid, self.scene_item_id, crop)
			self.prev_crop = crop
