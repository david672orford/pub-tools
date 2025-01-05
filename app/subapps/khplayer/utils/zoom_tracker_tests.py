from .zoom_tracker import ZoomTracker

def tracker_test_image(filename):
	"""Run the Zoom tracker on a screenshot image"""
	from time import sleep
	from PIL import Image, ImageDraw
	from .controllers import obs, ObsError

	img = Image.open(filename)
	if img.mode != "RGB":
		img = img.convert("RGB")
	tracker = ZoomTracker()
	tracker.load_image(img)

	class BoxDrawer:
		def __init__(self, img):
			self.draw = ImageDraw.Draw(img)
		def draw_box(self, box):
			self.draw.rectangle(((box.x, box.y), (box.x+box.width, box.y+box.height)), outline=(255, 0, 0), width=1)
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

def tracker_track():
	"""Run the Zoom tracker through OBS-Websocket"""
	from time import sleep
	import os
	from PIL import Image
	from flask import current_app
	from .controllers import obs, ObsError
	zoom_input_name = "Zoom Capture"
	filename = os.path.join(current_app.instance_path, zoom_input_name + ".png")
	class ZoomCropper:
		def __init__(self, source_name):
			self.prev_crop_box = None
			self.source_name = source_name
		def set_crop(self, crop_box):
			if crop_box != self.prev_crop_box:
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
				obs.set_input_settings(name=self.source_name, settings=settings)
				self.prev_crop_box = crop_box
	zoom_scenes = (
		ZoomCropper("Zoom Participant 0"),
		ZoomCropper("Zoom Participant 1"),
		ZoomCropper("Zoom Participant 2"),
		)
	tracker = ZoomTracker(debug=True)
	while True:
		try:
			print("Getting snapshot of Zoom window...")
			response = obs.request("SaveSourceScreenshot", {
				"sourceName": zoom_input_name,
				"imageFilePath": filename,
				"imageFormat": "png",
				"imageCompressionQuality": 50,
				})
			img = Image.open(filename).convert("RGB")
			tracker.load_image(img)
			tracker.do_cropping(zoom_scenes)
		except ObsError as e:
			print("OBS Error:", e)
		print()
		sleep(3)
