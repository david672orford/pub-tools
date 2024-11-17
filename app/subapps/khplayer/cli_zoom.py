from struct import pack
import os.path
from time import time, sleep
from dataclasses import dataclass

from flask import current_app
from flask.cli import AppGroup
import click
from PIL import Image, ImageDraw

from .utils.controllers import obs, ObsError

cli_zoom = AppGroup("zoom", help="Zoom scene control")

@cli_zoom.command("track", help="Track current speaker in Zoom window")
def cmd_zoom_track():
	zoom_input_name = "Zoom Capture"
	filename = os.path.join(current_app.instance_path, zoom_input_name + ".png")

	zoom_input_uuid = obs.get_input_uuid(zoom_input_name)
	assert zoom_input_uuid is not None, "%s not found" % zoom_input_name

	zoom_scenes = (
		ZoomCropper("* Zoom 0", zoom_input_name, zoom_input_uuid),
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
			i = 0
			for speaker_index in finder.speaker_indexes:
				crop = finder.layout[speaker_index] if speaker_index is not None and speaker_index < len(finder.layout) else False
				print(f"speaker_indexes[{i}] crop is {crop}")
				zoom_scenes[i].set_crop(crop)
				i += 1

		except ObsError as e:
			print("OBS Error:", e)

		print()
		sleep(3)

# We crop pieces out of the Zoom window by creating a series of scenes each
# of which has a single item which is the Zoom capture input. We do the
# cropping by setting the transform. This class finds or creates the
# pieces we need and warps them up into a neat little package.
class ZoomCropper:
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

@cli_zoom.command("test", help="Test the Zoom box finder")
@click.argument("filename")
def cmd_zoom_test(filename):
	finder = ZoomBoxFinder()
	img = Image.open(filename)
	finder.load_image(img)

	print("Participants zone:", finder.offsetx, finder.offsety, finder.width, finder.height)
	finder.draw_box(finder.offsetx, finder.offsety, finder.offsetx+finder.width, finder.offsety+finder.height)

	print("Speaker size:", finder.speaker.width, finder.speaker.height)
	finder.draw_box(finder.speaker.x, finder.speaker.y, finder.speaker.x+finder.speaker.width, finder.speaker.y+finder.speaker.height)

	print("Speaker index:", finder.speaker_indexes[0])

	for crop in finder.layout:
		finder.draw_box(crop["cropLeft"], crop["cropTop"], finder.img.width - crop["cropRight"], finder.img.height - crop["cropBottom"])

	finder.img.show()

#
# Given an image of the main Zoom window, find the box which contains each
# participant's video.
#
# https://pillow.readthedocs.io/en/stable/index.html
# https://realpython.com/image-processing-with-the-python-pillow-library/
# https://github.com/python-pillow/Pillow
#
class ZoomBoxFinder:
	speaker_border_color = pack("BBB", 35, 217, 89)			# green
	speaker_border_color_run = 300 * speaker_border_color	# smallest seems to be about 450px wide
	speaker_border_width = 4
	background_color = pack("BBB", 13, 13, 13)
	sidebar_color = pack("BBB", 255, 255, 255)
	corner_radius = 17
	bytes_per_pixel = 3
	grey_border_width = 5

	def __init__(self):
		self.debug = True
		self.prev_size = None
		self.speaker = None
		self.speaker_indexes = [None, None, None]
		self.speaker_switch_count = 0
		self.layout = []

	def load_image(self, img):

		# Load the screenshot of the Zoom window into self.img and self.data
		self._load_image(img)

		# Measure length of the black row at the very bottom. If it is much shorter
		# than the width of the image, then a side panel is open. Crop it off.
		self.sidebar_width = self._measure_sidebar(self.img.height - 5)
		if self.debug:
			print("sidebar_width:", self.sidebar_width)
		if self.sidebar_width > 0:
			if self.debug:
				print("Cropping...")
			self._load_image(self.img.crop((0, 0, self.img.width - self.sidebar_width, self.img.height)))

		# If the image size (after the cropping out of the side panel) has changed,
		# we can't work out the layout until we once again detect the green outline
		# of a current speaker.
		if self.img.size != self.prev_size:
			if self.debug:
				print("Image size has changed")
			self.speaker = None
			self.prev_size = self.img.size

		# Find the area in the center where the gallery view is
		self._find_gallery()

		# Look for the green border which indicates who is speaking
		self.speaker = self._find_speaker_box()

		# If someone is speaking, we know the size of a speaker box
		# and can work out where all the boxes are.
		if self.speaker is not None:
			self.speaker_indexes[0] = self._do_layout()

		# If there is a speaker and it is not one of the up to two speakers
		# previously identified, replace one of them alternating between the
		# first and the second.
		if self.speaker_indexes[0] is not None and self.speaker_indexes[0] not in self.speaker_indexes[1:]:
			self.speaker_indexes[self.speaker_switch_count % 2 + 1] = self.speaker_indexes[0]
			self.speaker_switch_count += 1

	def _load_image(self, img):
		print(img.format, img.width, img.height, img.mode)
		self.img = img
		self.data = self.img.tobytes()
		# Multiplier for the y-coordinate to find where a row starts in the
		# one-dimension image-data array
		self.row_length_in_bytes = self.img.width * self.bytes_per_pixel

	# Find the gallery view area by starting in the center of the screen
	# and moving up and down until we find all-black rows. Measure
	# the left margin both at the top and at the level of the last row.
	# Store the result in instance variables.
	def _find_gallery(self):

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

	# Count the number of black pixels at the start of the indicated row
	def _measure_left_margin(self, y):
		offset = (y * self.img.width + self.grey_border_width) * self.bytes_per_pixel
		for x in range(self.grey_border_width, self.img.width):
			if self.data.find(self.background_color, offset) != offset:
				return x - 1
			offset += self.bytes_per_pixel
		raise AssertionError("Reached far right without finding end of left margin")

	def _measure_sidebar(self, y):
		offset = (y * self.img.width + self.img.width - self.grey_border_width) * self.bytes_per_pixel
		for x in range(self.img.width - (2 * self.grey_border_width)):
			if self.data.find(self.sidebar_color, offset) != offset:
				return x
			offset -= self.bytes_per_pixel
		raise AssertionError("Reached far left without finding end of sidebar")

	# Find the position and size of the green border which surounds
	# the video box of the current speaker
	def _find_speaker_box(self):

		# Scan down looking for the top border. Bail out if we don't find it.
		hit1 = self.data.find(self.speaker_border_color_run)
		if hit1 == -1:
			return None
		x1 = int(hit1 % self.row_length_in_bytes / self.bytes_per_pixel)
		y1 = int(hit1 / self.row_length_in_bytes)
		if self.debug:
			print("hit1:", x1, y1)

		# Scan furthur down for the bottom border. Bail out if we don't find it.
		hit2 = self.data.find(self.speaker_border_color_run, hit1 + 50 * self.row_length_in_bytes)
		if hit2 == -1:
			return None
		x2 = int(hit2 % self.row_length_in_bytes / self.bytes_per_pixel)
		y2 = int(hit2 / self.row_length_in_bytes)
		if self.debug:
			print("hit2:", x2, y2)

		# Distance between top and bottom borders fidged a bit for line width
		height = y2 - y1 + self.speaker_border_width

		# The X positions of the start of the top and bottom borders will be a bit
		# different due to the fact that we hit it at different heights of the
		# rounded corner, but they should be close.
		assert (x2 - x1) < self.corner_radius

		return CropBox(
			# Move X back a bit since we hit the top border at the top of the rounded corner
			x = x1 - self.corner_radius,
			y = y1,
			height = height,
			# We do not measure the width, merely infer it from the expected 16:9 aspect ratio
			width = int(height * 16 / 9 + 2.5),
			)

	# Given:
	# 1) The dimensions of the gallery view
	# 2) The dimensions of the active speaker
	# work out the rows and columns of the grid
	def _do_layout(self):

		FUDGE = 10
		columns = int((self.width+FUDGE) / self.speaker.width)
		rows = int((self.height+FUDGE) / self.speaker.height)
		if self.debug:
			print(f"Gallery layout: {columns}x{rows}")
			print(f"Speaker: {self.speaker}")

		y = self.offsety
		self.layout = []
		speaker_index = None
		for row in range(rows):
			if row == (rows - 1):		# last row may not be full
				x = self.offset2x
				columns = int(self.width2 / self.speaker.width)
			else:
				x = self.offsetx
			for column in range(columns):
				if abs(x - self.speaker.x) < 10 and abs(y - self.speaker.y) < 10:
					speaker_index = len(self.layout)
				self.layout.append({
					"cropLeft": x,
					"cropTop": y,
					"cropRight": self.img.width + self.sidebar_width - self.speaker.width - x,
					"cropBottom": self.img.height - self.speaker.height - y,
					})
				x += self.speaker.width
			y += self.speaker.height

		if self.debug:
			for i in range(len(self.layout)):
				print(f"layout[{i}] = {repr(self.layout[i])}")
			print("speaker_index:", speaker_index)
		return speaker_index

	def draw_box(self, x1, y1, x2, y2):
		draw = ImageDraw.Draw(self.img)
		draw.rectangle(((x1, y1), (x2, y2)), outline=(255, 0, 0), width=1)

@dataclass
class CropBox:
	x: int
	y: int
	width: int
	height: int

