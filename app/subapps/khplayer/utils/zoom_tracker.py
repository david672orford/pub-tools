from struct import pack
from dataclasses import dataclass

@dataclass
class CropBox:
	x: int
	y: int
	width: int
	height: int

class ZoomTracker:
	"""
	Given an image of the main Zoom window, find the box which
	contains each participant's video.
	https://pillow.readthedocs.io/en/stable/index.html
	https://realpython.com/image-processing-with-the-python-pillow-library/
	https://github.com/python-pillow/Pillow
	"""

	SPEAKER_BORDER_COLOR = pack("BBB", 35, 217, 89)			# green
	SPEAKER_BORDER_COLOR_RUN = 300 * SPEAKER_BORDER_COLOR	# smallest seems to be about 450px wide
	SPEAKER_BORDER_WIDTH = 4
	SPEAKER_BORDER_LR = SPEAKER_BORDER_WIDTH * SPEAKER_BORDER_COLOR
	BACKGROUND_COLOR = pack("BBB", 13, 13, 13)
	SIDEBAR_COLOR = pack("BBB", 255, 255, 255)
	CORNER_RADIUS = 16
	BYTES_PER_PIXEL = 3
	GREY_BORDER_WIDTH = 5

	def __init__(self):
		self.debug = False
		self.speaker_indexes = SimpleSpeakerIndexes()
		self.gallery = None
		self.speaker_box = None
		self.layout = None

	def load_image(self, img):
		assert img.mode == "RGB", f"Unsupported image mode: {img.mode}"

		# Load the screenshot of the Zoom window into self.img and self.data
		self._load_image(img)

		# Measure length of the black row at the very bottom. If it is much shorter
		# than the width of the image, then a side panel is open. Crop it off.
		self.sidebar_width = self.measure_sidebar(self.img.height - 5)
		if self.debug:
			print("sidebar_width:", self.sidebar_width)
		if self.sidebar_width > 0:
			if self.debug:
				print("Cropping...")
			self._load_image(self.img.crop((0, 0, self.img.width - self.sidebar_width, self.img.height)))

		# Find the area in the center where the gallery view is
		gallery = self.find_gallery()

		# Look for the green border which indicates who is speaking
		speaker_box = self.find_speaker_box()

		# If someone is speaking, we know the size of a speaker box
		# and can work out where all the boxes are.
		if gallery is not None and speaker_box is not None:
			self.layout, speaker_index = self.do_layout(gallery, speaker_box)
			if self.debug:
				print("speaker_index:", speaker_index)
			self.speaker_indexes.set_speaker_index(speaker_index)
		else:
			self.layout = []

	def _load_image(self, img):
		if self.debug:
			print(img.format, img.width, img.height, img.mode)
		self.img = img
		self.data = self.img.tobytes()
		# Multiplier for the y-coordinate to find where a row starts in the
		# one-dimension image-data array
		self.row_length_in_bytes = self.img.width * self.BYTES_PER_PIXEL

	# Find the gallery view area by starting in the center of the screen
	# and moving up and down until we find all-black rows. Measure
	# the left margin both at the top and at the level of the last row.
	# Store the result in instance variables.
	def find_gallery(self):
		# An entire horizontal row of 'black' pixels, minus the very ends which are grayer.
		BACKGROUND_COLOR_row = (self.img.width - 2 * self.GREY_BORDER_WIDTH) * self.BACKGROUND_COLOR

		# Index of far-left pixel halfway down the window
		middle = int(self.img.height / 2 * self.row_length_in_bytes)

		# Search upward from the middle for the first all-black row. This is the top of the gallery.
		top = self.data.rfind(BACKGROUND_COLOR_row, 0, middle)
		if top == -1:
			return None

		# Search downward from the middle for the first all-black row. This is the bottom of the gallery.
		bottom = self.data.find(BACKGROUND_COLOR_row, middle)
		if bottom == -1:
			return None

		# Convert indexes into self.data[] of the top and the bottom of the gallery into y-coordinates
		top = self.offset_to_y(top)
		bottom = self.offset_to_y(bottom)

		# Measure the left margin at a point near the top of the gallery.
		left_margin = self.measure_left_margin(top + 50)

		# Compute the image location based on these all-black rows and columns
		gallery = CropBox(
			x = left_margin + 1,
			y = top + 1,
			width = self.img.width - (2 * left_margin) - 2,
			height = bottom - top - 1,
			)

		# Re-measure the left margin at a point near the bottom of the gallery.
		# If the number of participant images does not fill the last row,
		# the row is centered leading to a larger left margin.
		left_margin = self.measure_left_margin(bottom - 50)
		gallery.x2 = left_margin + 1
		gallery.width2 = self.img.width - (2 * left_margin) - 2

		return gallery

	def measure_left_margin(self, y):
		"""Count the number of black pixels at the start of the indicated row"""
		offset = (y * self.img.width + self.GREY_BORDER_WIDTH) * self.BYTES_PER_PIXEL
		for x in range(self.GREY_BORDER_WIDTH, self.img.width):
			if self.data.find(self.BACKGROUND_COLOR, offset) != offset:
				return x - 1
			offset += self.BYTES_PER_PIXEL
		raise AssertionError("Reached far right without finding end of left margin")

	def measure_sidebar(self, y):
		"""Measure the white sidebar based on a row at the very bottom of window"""
		offset = (y * self.img.width + self.img.width - self.GREY_BORDER_WIDTH) * self.BYTES_PER_PIXEL
		for x in range(self.img.width - (2 * self.GREY_BORDER_WIDTH)):
			if self.data.find(self.SIDEBAR_COLOR, offset) != offset:
				return x
			offset -= self.BYTES_PER_PIXEL
		raise AssertionError("Reached far left without finding end of sidebar")

	def find_speaker_box(self):
		"""
		Find the position and size of the green border which surounds
		the video box of the current speaker
		"""

		# Scan down looking for the top border. Bail out if we don't find it.
		hit1 = self.data.find(self.SPEAKER_BORDER_COLOR_RUN)
		if hit1 == -1:
			return None
		x1, y1 = self.offset_to_xy(hit1)
		if self.debug:
			print("hit1:", x1, y1)

		# Scan further down for the bottom border. Bail out if we don't find it.
		hit2 = self.data.find(self.SPEAKER_BORDER_COLOR_RUN, hit1 + 50 * self.row_length_in_bytes)
		if hit2 == -1:
			return None
		x2, y2 = self.offset_to_xy(hit2)
		if self.debug:
			print("hit2:", x2, y2)

		# The X positions of the start of the top and bottom borders will be a bit
		# different due to the fact that hit1 and hit2 hit it at different heights of the
		# rounded corner, but they should be close.
		if (x2 - x1) > self.CORNER_RADIUS:
			return None

		# Distance between the tops of the top and bottom borders plus the
		# border width is the height of the speaker box.
		height = y2 - y1 + self.SPEAKER_BORDER_WIDTH

		# Estimate positions of left and right edges of the box
		x = x1 - self.CORNER_RADIUS
		width = int(height * 16 / 9 + 0.5)
		if self.debug:
			print(f"Estimates: x={x}, width={width}")

		# Use our estimates to find the right and left borders and measure their actual positions.
		middle_y = y1 + int(height / 2)
		FUDGE = 5
		lb_hit = self.data.find(
			self.SPEAKER_BORDER_LR,
			self.xy_to_offset(x - FUDGE, middle_y),
			self.xy_to_offset(x + self.SPEAKER_BORDER_WIDTH + FUDGE, middle_y),
			)
		if lb_hit != -1:
			x = self.offset_to_x(lb_hit)
		else:
			print("Failed to find right border")
		rb_hit = self.data.find(
			self.SPEAKER_BORDER_LR,
			self.xy_to_offset(x + width - self.SPEAKER_BORDER_WIDTH - FUDGE, middle_y),
			self.xy_to_offset(x + width + FUDGE, middle_y),
			)
		if rb_hit != -1:
			width = int((rb_hit - lb_hit) / self.BYTES_PER_PIXEL + self.SPEAKER_BORDER_WIDTH)
		else:
			print("Failed to find right border")
		if self.debug:
			print(f"Final: x={x}, width={width}")

		return CropBox(x, y1, width, height)

	def do_layout(self, gallery, speaker_box):
		"""
		Given:
		1) The dimensions of the gallery view
		2) The dimensions of the active speaker
		work out the rows and columns of the grid
		"""

		FUDGE = 10
		columns = int((gallery.width+FUDGE) / speaker_box.width)
		rows = int((gallery.height+FUDGE) / speaker_box.height)
		if self.debug:
			print(f"Gallery layout: {columns}x{rows}")
			print(f"Speaker box: {speaker_box}")

		y = gallery.y
		layout = []
		speaker_index = None
		for row in range(rows):
			if row == (rows - 1):		# last row may not be full
				x = gallery.x2
				columns = int(gallery.width2 / speaker_box.width)
			else:
				x = gallery.x
			for column in range(columns):
				if abs(x - speaker_box.x) < 10 and abs(y - speaker_box.y) < 10:
					speaker_index = len(layout)
				layout.append(CropBox(
					x = x,
					y = y,
					width = speaker_box.width,
					height = speaker_box.height,
					))
				x += speaker_box.width
			y += speaker_box.height

		if self.debug:
			for i in range(len(layout)):
				print(f"layout[{i}] = {repr(layout[i])}")
			print("speaker_index:", speaker_index)

		return layout, speaker_index

	def do_cropping(self, zoom_scenes):
		"""Set the crop boxes on the supplied ZoomCropper objects"""
		width = self.img.width + self.sidebar_width
		height = self.img.height
		i = 0
		for speaker_index in self.speaker_indexes:
			crop = self.layout[speaker_index] if speaker_index is not None and speaker_index < len(self.layout) else False
			if self.debug:
				print(f"speaker_indexes[{i}] crop is {crop}")
			zoom_scenes[i].set_crop(crop, width, height)
			i += 1

	def offset_to_xy(self, offset):
		assert type(offset) is int
		return (
			self.offset_to_x(offset),
			self.offset_to_y(offset),
			)

	def offset_to_x(self, offset):
		assert type(offset) is int
		return offset % self.row_length_in_bytes // self.BYTES_PER_PIXEL

	def offset_to_y(self, offset):
		assert type(offset) is int
		return offset // self.row_length_in_bytes

	def xy_to_offset(self, x, y):
		assert type(x) is int
		assert type(y) is int
		return y * self.row_length_in_bytes + x * self.BYTES_PER_PIXEL

class SimpleSpeakerIndexes(list):
	"""
	Track current speaker and current pair of speakers

	Index 0: current speaker
	Indexes 1 and 2: current and immediately previous speaker

	As new speakers appear they will replace 1 and 2 alternately.
	"""
	def __init__(self):
		self.extend((None, None, None))
		self.speaker_switch_count = 0

	def set_speaker_index(self, speaker_index):

		# OBS is the "speaker" or no change
		if speaker_index in (0, self[0]):
			return

		# Set current speaker
		self[0] = speaker_index

		# If current speaker is not 1 or 2, replace the one changed least recently.
		if speaker_index not in self[1:]:
			self[self.speaker_switch_count % 2 + 1] = speaker_index
			self.speaker_switch_count += 1
