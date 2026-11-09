"""Track the layout and speaker locations in a Zoom video conference window"""

from dataclasses import dataclass
from io import BytesIO
from struct import pack
from typing import Final
import logging

from PIL import Image

logger = logging.getLogger(__name__)

@dataclass
class CropBox:
	"""A rectanguler segment of the Zoom video conference window"""
	x: int
	y: int
	width: int
	height: int

@dataclass
class GalleryCropBox(CropBox):
	"""Position of the Zoom participant gallery in the window"""
	x2: int				# left margin of last row
	width2: int			# width in pixels of last row

@dataclass
class SpeakerCropBox(CropBox):
	"""Position of the green frame representing the current speaker"""
	border_width: int

class Layout(list[CropBox]):
	"""The speaker positions and current speaker"""
	def __init__(self):
		super().__init__()
		self.speaker_index:int|None = None

class ZoomCropperBase:
	"""Object used pass callbacks to do_cropping()"""
	def set_crop_box(self, crop_box:CropBox|None|bool) -> None:
		print("Not implemented:", crop_box)

class ZoomTracker:
	"""
	Given an image of the main Zoom window, find the box which
	contains each participant's video.
	https://pillow.readthedocs.io/en/stable/index.html
	https://github.com/python-pillow/Pillow
	https://realpython.com/image-processing-with-the-python-pillow-library/
	"""

	BYTES_PER_PIXEL: Final[int] = 3											# Red, Green, Blue
	SEARCH_CELLSPACING: Final[int] = 10										# Set greater than spacing between gallery cells
	SPEAKER_BORDER_COLOR: Final[bytes] = pack("BBB", 35, 217, 89)			# Green border around current speaker
	SPEAKER_BORDER_COLOR_RUN: Final[bytes] = 300 * SPEAKER_BORDER_COLOR		# Smallest seems to be about 450px wide

	def __init__(self, debug:bool=False):
		self.debug:bool = debug

		self.gallery:GalleryCropBox
		self.layout:Layout = Layout()
		self.speaker_indexes:SimpleSpeakerIndexes = SimpleSpeakerIndexes()

		self.img:Image.Image
		self.data:bytes
		self.row_length_in_bytes:int
		self.background_color:bytes

	def set_exclude_first_box(self, exclude_first_box:bool):
		"""Never treat the first box as the speaker, it is the OBS output"""
		self.speaker_indexes.exclude_first_box = exclude_first_box

	def set_speaker_index(self, index:int) -> None:
		"""Force the current speaker"""
		if 0 <= index < len(self.layout):
			self.speaker_indexes.set_speaker_index(index)
		else:
			logger.error("Invalid speaker index: %d", index)

	def reset_speakers(self):
		"""Clear present and previous speaker until new detection"""
		self.speaker_indexes.reset_speakers()

	def do_cropping(self, zoom_scenes:list[ZoomCropperBase]):
		"""Set the crop boxes on the supplied ZoomCropper objects"""
		if self.debug:
			print("Setting OBS croppers...")
		for i, speaker_index in enumerate(self.speaker_indexes):
			crop_box = self.layout[speaker_index] if speaker_index is not None and speaker_index < len(self.layout) else False
			if self.debug:
				print(f" Source \"Zoom Participant {i}\" -> Speaker {speaker_index} of {len(self.layout)}, crop_box={crop_box}")
			zoom_scenes[i].set_crop_box(crop_box)

	def get_gallery_image(self) -> BytesIO|None:
		"""Get a JPEG cropped to the Zoom participant gallery"""
		if hasattr(self, "gallery"):
			g = self.gallery
			image = self.img.crop((g.x, g.y, g.x+g.width, g.y+g.height))
		else:
			image = Image.new("RGB", (320, 160), color=(100, 100, 100))
		assert type(image) is Image.Image
		buffer = BytesIO()
		image.save(buffer, format="JPEG", quality=85)
		_ = buffer.seek(0)
		return buffer

	def load_image(self, img:Image.Image):
		"""Analyze an screenshot of the main Zoom window and figure out the speaker positions"""

		if self.debug:
			print("Loading image...")

		assert img.mode == "RGB", f"Unsupported image mode: {img.mode}"

		# Load the screenshot of the Zoom window into self.img and self.data
		self._load_image(img)

		# Take the bottom left pixel as the background color
		offset = self.xy_to_offset(0, self.img.height-1)
		self.background_color = self.data[offset:offset+3]

		main_width = self.measure_left_margin(self.img.height-1)
		if self.debug:
			print(" Main pane width:", main_width)
		if 0 < main_width < self.img.width:
			self._load_image(self.img.crop((0, 0, main_width, self.img.height)))

		# Find the area in the center where the gallery view is
		self.gallery = self.find_gallery()

		# Look for the green border which indicates who is speaking
		speaker_box:SpeakerCropBox = self.find_speaker_box()

		# If someone is speaking, we know the size of a speaker box
		# and can work out where all the boxes are.
		if speaker_box is not None:
			self.layout = self.infer_layout(speaker_box)
			self.speaker_indexes.set_speaker_index(self.layout.speaker_index)
		else:
			self.layout = Layout()

	def _load_image(self, img:Image.Image):
		if self.debug:
			print(" Image format:", img.format, img.width, img.height, img.mode)
		self.img = img
		self.data = self.img.tobytes()
		self.row_length_in_bytes = self.img.width * self.BYTES_PER_PIXEL

	def measure_left_margin(self, y:int) -> int:
		"""Count the number of background-color pixels at the start of the indicated row"""
		offset = self.xy_to_offset(0, y)
		for x in range(self.img.width):
			if self.data.find(self.background_color, offset, offset+self.BYTES_PER_PIXEL) != offset:
				break
			offset += self.BYTES_PER_PIXEL
		else:
			x += 1
		return x

	def find_gallery(self) -> GalleryCropBox:
		"""
		Find the gallery view area by starting in the center of the screen
		and moving up and down until we find all-black rows. Measure
		the left margin both at the top and at the level of the last row.
		Store the result in instance variables.
		"""
		if self.debug:
			print("Finding gallery area in Zoom screenshot...")

		# One row of background-color pixels
		background_color_row = self.img.width * self.background_color

		offset_limit = self.img.height * self.row_length_in_bytes
		data = memoryview(self.data)

		# Move down through the header until we a background-color row
		for offset1 in range(0, offset_limit, self.row_length_in_bytes):
			if data[offset1:offset1+self.row_length_in_bytes] == background_color_row:
				break

		# Move down through the background color until we hit the gallery
		for offset2 in range(offset1+self.row_length_in_bytes, offset_limit, self.row_length_in_bytes):
			if data[offset2:offset2+self.row_length_in_bytes] != background_color_row:
				break
		top = self.offset_to_y(offset2)
		if self.debug:
			print(f" Top: {top}")

		# Search downward from the middle until we hit a multiple background-color rows.
		run_length = 0
		for offset3 in range(int(offset_limit / 2), offset_limit, self.row_length_in_bytes):
			if data[offset3:offset3+self.row_length_in_bytes] != background_color_row:
				run_length = 0
			else:
				run_length += 1
				if run_length == self.SEARCH_CELLSPACING:
					break
		bottom = self.offset_to_y(offset3) - run_length
		if self.debug:
			print(f" Bottom: {bottom}")

		# Measure the left margin at a point near the top of the gallery.
		left_margin = self.measure_left_margin(top + 50)
		if self.debug:
			print(f" Left margin: {left_margin}")
		assert left_margin <= self.img.width

		# Re-measure the left margin at a point near the bottom of the gallery.
		# If the number of participant images does not fill the last row,
		# the row is centered leading to a larger left margin.
		last_left_margin = self.measure_left_margin(bottom - 50)
		if self.debug:
			print(f" Last row left margin: {last_left_margin}")

		# Compute the image location based on these all-black rows and columns
		gallery = GalleryCropBox(
			x = left_margin + 1,
			y = top,
			width = self.img.width - (2 * left_margin) - 3,
			height = bottom - top,
			x2 = last_left_margin + 1,
			width2 = self.img.width - (2 * last_left_margin) - 3,
			)

		if self.debug:
			print(f" {gallery}")

		return gallery

	def find_speaker_box(self) -> SpeakerCropBox|None:
		"""
		Find the position and size of the green border which surrounds
		the video box of the current speaker
		"""

		if self.debug:
			print("Finding speaker box in Zoom screenshot...")

		# Scan down looking for the top border. Bail out if we don't find it.
		hit1 = self.data.find(self.SPEAKER_BORDER_COLOR_RUN)
		if hit1 == -1:
			if self.debug:
				print(" Speaker box top not found")
			return None
		x1, y1 = self.offset_to_xy(hit1)
		if self.debug:
			print(f" Top found at: ({x1}, {y1})")

		# Scan further down for the bottom border. Bail out if we don't find it.
		hit2 = self.data.find(self.SPEAKER_BORDER_COLOR_RUN, hit1 + 50 * self.row_length_in_bytes)
		if hit2 == -1:
			if self.debug:
				print(" Speaker box bottom not found")
			return None
		x2, y2 = self.offset_to_xy(hit2)
		if self.debug:
			print(f" Bottom found at: ({x2}, {y2})")

		for yscan in range(y1+1, y1 + 20):
			offset = self.xy_to_offset(x1, yscan)
			if self.data.find(self.SPEAKER_BORDER_COLOR, offset, offset+self.BYTES_PER_PIXEL) != offset:
				border_width = (yscan - y1)
				break
		else:
			raise AssertionError("Speaker border implausibly wide")
		if self.debug:
			print(" Border width:", border_width)

		# The X positions of the start of the top and bottom borders will be a bit
		# different due to the fact that hit1 and hit2 hit it at different heights of the
		# rounded corner, but they should be close.
		# NOTE: This test is disabled because blending of the participant name at the lower left
		# can sometimes alter the shade of the border.
		border_corner_radius = border_width * 4
		#if (x2 - x1) > border_corner_radius:
		#	print(f" Funky values: ({x1}, {y1}) ({x2}, {y2})")
		#	return None

		# Distance between tops of the top and bottom borders, plus the
		# border width, is the height of the speaker box.
		height = y2 - y1 + border_width

		# Estimate positions of left and right edges of the box
		x = x1 - border_corner_radius
		width = int(height * 16 / 9 + 0.5)

		# Use our estimates to find the left border and measure its actual position.
		middle_y = y1 + int(height / 2)
		if self.debug:
			print(f" Estimates: x={x}, middle_y={middle_y}, border_width={border_width}, width={width}")
		FUDGE = 10
		border_lr = (border_width-1) * self.SPEAKER_BORDER_COLOR
		lb_hit = self.data.find(
			border_lr,
			self.xy_to_offset(x - FUDGE, middle_y),
			self.xy_to_offset(x + border_width + FUDGE, middle_y),
			)
		if lb_hit == -1:
			print(" Failed to find left border")
			return None
		x = self.offset_to_x(lb_hit)

		# Use our estimates to find the left border and measure its actual position.
		rb_hit = self.data.find(
			border_lr,
			self.xy_to_offset(x + width - border_width - FUDGE, middle_y),
			self.xy_to_offset(x + width + FUDGE, middle_y),
			)
		if rb_hit == -1:
			print(" Failed to find right border")
			return None
		width = int((rb_hit - lb_hit) / self.BYTES_PER_PIXEL + border_width)
		if self.debug:
			print(f" Final location: x={x}, y={y1}, width={width}, height={height}")

		return SpeakerCropBox(x, y1, width, height, border_width)

	def infer_layout(self, speaker_box:SpeakerCropBox) -> Layout:
		"""
		Given:
		1) The dimensions of the gallery view
		2) The dimensions of the active speaker
		work out the rows and columns of the grid
		"""

		assert speaker_box is not None
		FUDGE = 10
		columns = int((self.gallery.width+FUDGE) / speaker_box.width)
		rows = int((self.gallery.height+FUDGE) / speaker_box.height)
		x_cellspacing = self.gallery.width - (speaker_box.width * columns)
		y_cellspacing = self.gallery.height - (speaker_box.height * rows)

		if self.debug:
			print("Inferring gallery speaker layout...")
			print(f" Grid dimensions: {columns} x {rows}")
			print(f" Cell spacing: {x_cellspacing} {y_cellspacing}")

		y = self.gallery.y
		layout = Layout()
		border_width = speaker_box.border_width
		double_border_width = border_width * 2
		for row in range(rows):
			if row == (rows - 1):		# last row may not be full
				x = self.gallery.x2
				columns = int((self.gallery.width2 + FUDGE) / speaker_box.width)
			else:
				x = self.gallery.x
			for _ in range(columns):
				if abs(x - speaker_box.x) < 10 and abs(y - speaker_box.y) < 10:
					layout.speaker_index = len(layout)
				layout.append(CropBox(
					x = x + border_width,
					y = y + border_width,
					width = speaker_box.width - double_border_width,
					height = speaker_box.height - double_border_width,
					))
				x += speaker_box.width
				x += x_cellspacing
			y += speaker_box.height
			y += y_cellspacing

		if self.debug:
			for i in range(len(layout)):
				print(f" Speaker box {i} at: {layout[i]!r}", "<-- Current" if i == layout.speaker_index else "")

		return layout

	def offset_to_xy(self, offset:int):
		"""Convert a byte offset into the PIL data array into the (x,y) pixel position"""
		assert type(offset) is int
		return (
			self.offset_to_x(offset),
			self.offset_to_y(offset),
			)

	def offset_to_x(self, offset:int) -> int:
		assert type(offset) is int
		return offset % self.row_length_in_bytes // self.BYTES_PER_PIXEL

	def offset_to_y(self, offset:int) -> int:
		assert type(offset) is int
		return offset // self.row_length_in_bytes

	def xy_to_offset(self, x:int, y:int) -> int:
		"""Convert an (x, y) pixel position into an offset into the PIL data array"""
		assert type(x) is int
		assert type(y) is int
		return y * self.row_length_in_bytes + x * self.BYTES_PER_PIXEL

class SimpleSpeakerIndexes(list[None|int]):
	"""
	Track current speaker and current pair of speakers

	Index 0: current speaker
	Indexes 1 and 2: current and immediately previous speaker

	As new speakers appear they will replace 1 and 2 alternately.
	"""
	def __init__(self):
		super().__init__()
		self.extend((None, None, None))
		self.speaker_switch_count:int = 0
		self.exclude_first_box:bool = True

	def reset_speakers(self):
		for i in range(len(self)):
			self[i] = None

	def set_speaker_index(self, speaker_index:int|None):

		# First box is generally the one showing OBS output
		if speaker_index == 0 and self.exclude_first_box:
			return

		# No change
		if speaker_index == self[0]:
			return

		# Set current speaker
		self[0] = speaker_index

		# If current speaker is not 1 or 2, replace the one changed least recently.
		if speaker_index not in self[1:]:
			self[self.speaker_switch_count % 2 + 1] = speaker_index
			self.speaker_switch_count += 1
