"""
CLI for the Zoom tracker
"""

import os.path
from time import time, sleep

from flask import current_app
from flask.cli import AppGroup
import click
from PIL import Image, ImageDraw

from .utils.controllers import obs, ObsError
from .utils.zoom_tracker import ZoomTracker

cli_zoom = AppGroup("zoom", help="Zoom conferencing integration")

@cli_zoom.command("configure")
def cmd_zoom_configure():
	"""Change Zoom settings to work with KHPlayer"""
	pass

@cli_zoom.command("test")
@click.argument("filename")
def cmd_zoom_test(filename):
	"""Test the Zoom tracker on an image"""

	img = Image.open(filename)
	if img.mode != "RGB":
		img = img.convert("RGB")
	tracker = ZoomTracker()
	tracker.load_image(img)
	drawer = BoxDrawer(tracker.img)

	gallery = tracker.find_gallery()
	speaker_box = tracker.find_speaker_box()

	print("Gallery:", gallery)
	if gallery is not None:
		print("x2:", gallery.x2)
		print("width2:", gallery.width2)
		drawer.draw_box(gallery)
	print("Speaker box:", speaker_box)
	if speaker_box is not None:
		drawer.draw_box(speaker_box)
	print("Layout:", tracker.layout)
	print("Speaker indexes:", tracker.speaker_indexes)
	for box in tracker.layout:
		drawer.draw_box(box)

	tracker.img.show()

class BoxDrawer:
	def __init__(self, img):
		self.draw = ImageDraw.Draw(img)
	def draw_box(self, box):
		self.draw.rectangle(((box.x, box.y), (box.x+box.width, box.y+box.height)), outline=(255, 0, 0), width=1)

@cli_zoom.command("track")
def cmd_zoom_track():
	"""Run the Zoom tracker through OBS-Websocket"""
	zoom_input_name = "Zoom Capture"
	filename = os.path.join(current_app.instance_path, zoom_input_name + ".png")

	zoom_input_uuid = obs.get_input_uuid(zoom_input_name)
	assert zoom_input_uuid is not None, "%s not found" % zoom_input_name

	zoom_scenes = (
		ZoomCropper("Zoom Participant 0", zoom_input_name, zoom_input_uuid),
		ZoomCropper("Zoom Participant 1", zoom_input_name, zoom_input_uuid),
		ZoomCropper("Zoom Participant 2", zoom_input_name, zoom_input_uuid),
		)

	tracker = ZoomTracker(debug=True)

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

			# Load into our box tracker and try to figure out the layout
			tracker.load_image(img)

			# Adjust the cropping on all of the Zoom scenes
			tracker.do_cropping(zoom_scenes)

		except ObsError as e:
			print("OBS Error:", e)

		print()
		sleep(3)

class ZoomCropper:
	"""
	Wrapper for an OBS scene which contains a cropped version of the Zoom screen capture
	There is an OBS-API version of this in khplayer-zoom-tracker.py.
	"""

	def __init__(self, source_name, zoom_input_name, zoom_input_uuid):
		self.prev_crop_box = None
		self.input_uuid = obs.get_input_uuid(source_name)

	def set_crop(self, crop_box):
		if self.input_uuid is not None and crop_box != self.prev_crop_box:
			if crop_box is False:
				settings = {"enabled": False}
			else:
				settings = {
					"enabled": True,
					"crop_x": crop_box.x,
					"crop_y": crop_box.y,
					"crop_width": crop_box.width,
					"crop_height": crop_box.height,
					}
			obs.set_input_settings(uuid=self.input_uuid, settings=settings)
			self.prev_crop_box = crop_box
