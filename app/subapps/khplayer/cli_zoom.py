from struct import pack
import os.path
from time import time, sleep

from flask.cli import AppGroup
import click
from PIL import Image, ImageDraw

from .utils.controllers import obs, ObsError

cli_zoom = AppGroup("zoom", help="Zoom scene control")

@cli_zoom.command("track", help="Track current speaker in Zoom window")
def cmd_zoom_track():
	zoom_input_name = "Zoom Capture"
	filename = os.path.abspath(zoom_input_name + ".png")

	zoom_input_uuid = obs.get_input_uuid(zoom_input_name)
	assert zoom_input_uuid is not None

	finder = ZoomBoxFinder()
	zoom0 = ZoomCropper(finder, "Zoom 0", zoom_input_name, zoom_input_uuid)
	zoom1 = ZoomCropper(finder, "Zoom 1", zoom_input_name, zoom_input_uuid)
	zoom2 = ZoomCropper(finder, "Zoom 2", zoom_input_name, zoom_input_uuid)

	while True:
		print("Getting snapshot...")
		try:
			start = time()
			response = obs.request("SaveSourceScreenshot", {
				"sourceUuid": zoom_input_uuid,
				"imageFormat": "png",
				"imageFilePath": filename,
				"imageCompressionQuality": 50,
				})
			print("Elapsed: %dms" % int((time() - start) * 1000))
		except ObsError as e:
			print("OBS Error:", e)
			coords = None

		img = Image.open(filename).convert("RGB")
		finder.load_image(img)

		if finder.speaker_index is not None:
			zoom0.set_crop(finder.layout[finder.speaker_index])
		if finder.speaker_indexes[0] is not None:
			zoom1.set_crop(finder.layout[finder.speaker_indexes[0]])
		if finder.speaker_indexes[1] is not None:
			zoom2.set_crop(finder.layout[finder.speaker_indexes[1]])

		print()
		sleep(2)

# An OBS scene with the Zoom window capture which we crop by setting the transform
class ZoomCropper:
	def __init__(self, finder, scene_name, zoom_input_name, zoom_input_uuid):
		self.finder = finder
		self.prev_crop = None

		self.scene_uuid = obs.get_scene_uuid(scene_name)
		if self.scene_uuid is None:
			self.scene_uuid = obs.create_scene(scene_name)["sceneUuid"]

		self.scene_item_id = obs.get_scene_item_id(self.scene_uuid, zoom_input_name)
		if self.scene_item_id is None:
			self.scene_item_id = obs.create_scene_item(scene_uuid=self.scene_uuid, source_uuid=zoom_input_uuid)

	def set_crop(self, box):
		x, y = box
		crop = {
			"cropLeft": x,
			"cropTop": y,
			"cropRight": self.finder.img.width - self.finder.speaker_width - x,
			"cropBottom": self.finder.img.height - self.finder.speaker_height - y,
			}
		if crop != self.prev_crop:
			obs.scale_scene_item(self.scene_uuid, self.scene_item_id, crop)
			self.prev_crop = crop

@cli_zoom.command("test", help="Test the Zoom box finder")
@click.argument("filename")
def cmd_zoom_test(filename):
	finder = ZoomBoxFinder()
	img = Image.open(filename)
	finder.load_image(img)

	print("Participants zone:", finder.offsetx, finder.offsety, finder.width, finder.height)
	finder.draw_box(finder.offsetx, finder.offsety, finder.offsetx+finder.width, finder.offsety+finder.height)

	print("Speaker size:", finder.speaker_width, finder.speaker_height)
	finder.draw_box(finder.speakerx, finder.speakery, finder.speakerx+finder.speaker_width, finder.speakery+finder.speaker_height)

	print("Speaker index:", finder.speaker_index)

	for x, y in finder.layout:
		finder.draw_box(x, y, x + finder.speaker_width, y + finder.speaker_height)

	finder.img.show()

#
# https://pillow.readthedocs.io/en/stable/index.html
# https://realpython.com/image-processing-with-the-python-pillow-library/
# https://github.com/python-pillow/Pillow
#
class ZoomBoxFinder:
	speaker_border_color = pack("BBB", 35, 217, 89)		# green
	speaker_border_color_run = 50 * speaker_border_color
	background_color = pack("BBB", 13, 13, 13)
	corner_radius = 16
	bytes_per_pixel = 3
	grey_border_width = 5

	def __init__(self):
		self.speaker_indexes = [None, None]
		self.speaker_switch_count = 0

	def load_image(self, img):
		"""Load a PIL image and find the area of interest"""

		self._load_image(img)

		# Measure black row length at the very bottom. If it is much shorter than the
		# width of the image, then a side panel is open. Crop it off.
		main_width = self._measure_left_margin(self.img.height - 5)
		#print("main_width:", main_width)
		if (self.img.width - main_width) > 10:
			#print("Cropping...")
			self._load_image(self.img.crop((0, 0, main_width, self.img.height)))

		self.row_length_in_bytes = self.img.width * self.bytes_per_pixel
		self._crop_to_participants()
		self._find_speaker_box()
		self._do_layout()

		# If there is a speaker and it is not one of the up to two speakers
		# previously identified, replace one of them alternating between the
		# first and the second.
		if self.speaker_index is not None and self.speaker_index not in self.speaker_indexes:
			self.speaker_indexes[self.speaker_switch_count % 2] = self.speaker_index
			self.speaker_switch_count += 1

	def _load_image(self, img):
		print(img.format, img.width, img.height, img.mode)
		self.img = img
		self.data = self.img.tobytes()

	def _crop_to_participants(self):

		# An entire horizontal row of 'black' pixels, minus the very ends which are grayer.
		background_color_row = (self.img.width - 2 * self.grey_border_width) * self.background_color

		# Short horizontal row of black pixels for measuring the left margin
		background_color_margin = 50 * self.background_color

		# Far-left pixel halfway down the window
		middle = int(self.img.height / 2 * self.row_length_in_bytes)

		# Search upward from the middle for the first all-black row. This is the top.
		top = int(self.data.rindex(background_color_row, 0, middle) / self.row_length_in_bytes)

		# Search downward from the middle for the first all-black row. This is the bottom.
		bottom = int(self.data.index(background_color_row, middle) / self.row_length_in_bytes)

		# Measure the left margin. We will assume the right is of the same width.
		left_margin = self._measure_left_margin(top + 25)

		# Compute the image location based on these all-black rows and columns
		self.offsetx = left_margin + 1
		self.offsety = top + 1
		self.width = self.img.width - (2 * self.offsetx) - 2
		self.height = bottom - top - 1

		# If the number of participant images does not fill the last row,
		# the row is centered leading to a larger left margin.
		left_margin = self._measure_left_margin(bottom - 25)
		self.offset2x = left_margin
		self.width2 = self.img.width - (2 * left_margin)

	def _measure_left_margin(self, y):
		offset = (y * self.img.width + self.grey_border_width) * self.bytes_per_pixel
		for x in range(self.grey_border_width, self.img.width):
			if self.data.find(self.background_color, offset) != offset:
				return x - 1
			offset += self.bytes_per_pixel
		raise AssertionError("Reached center without finding and of left margin")

	def _find_speaker_box(self):

		try:
			hit1 = self.data.index(self.speaker_border_color_run)
			x1 = int(hit1 % self.row_length_in_bytes / self.bytes_per_pixel)
			y1 = int(hit1 / self.row_length_in_bytes)
			print("hit1:", x1, y1)
	
			hit2 = self.data.index(self.speaker_border_color_run, hit1 + 50 * self.row_length_in_bytes)
			x2 = int(hit2 % self.row_length_in_bytes / self.bytes_per_pixel)
			y2 = int(hit2 / self.row_length_in_bytes)
			print("hit2:", x2, y2)
	
			assert (x2 - x1) < self.corner_radius
			self.speakerx = x1 - self.corner_radius
			self.speakery = y1
			self.speaker_height = y2 - y1 + 4
			self.speaker_width = int(self.speaker_height * 16 / 9)

		except ValueError:
			self.speakerx = self.offsetx
			self.speakery = self.offsety
			self.speaker_width = self.width
			self.speaker_height = self.height

	def _do_layout(self):
		columns = int(self.width / self.speaker_width)
		rows = int(self.height / self.speaker_height)
		y = self.offsety
		self.layout = []
		self.speaker_index = None
		for row in range(rows):
			if row == (rows - 1):		# last row
				x = self.offset2x
				columns = int(self.width2 / self.speaker_width)
			else:
				x = self.offsetx
			for column in range(columns):
				if abs(x - self.speakerx) < 5 and abs(y - self.speakery) < 5:
					self.speaker_index = len(self.layout)
				self.layout.append((x, y))
				x += self.speaker_width
			y += self.speaker_height

	def draw_box(self, x1, y1, x2, y2):
		draw = ImageDraw.Draw(self.img)
		draw.rectangle(((x1, y1), (x2, y2)), outline=(255, 0, 0), width=1)

