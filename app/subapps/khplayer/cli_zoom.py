from struct import pack
import os.path
from time import time, sleep

from flask.cli import AppGroup
from PIL import Image, ImageDraw

from .utils.controllers import obs

cli_zoom = AppGroup("zoom", help="Zoom scene control")

@cli_zoom.command("track", help="Track current speaker in Zoom window")
def cmd_zoom_track():
	zoom_input_name = "Zoom Capture"

	zoom_input_uuid = obs.get_input_uuid(zoom_input_name)
	assert zoom_input_uuid is not None

	zoom0 = get_zoom_cropper("Zoom 0", zoom_input_name, zoom_input_uuid)
	zoom1 = get_zoom_cropper("Zoom 1", zoom_input_name, zoom_input_uuid)
	zoom2 = get_zoom_cropper("Zoom 2", zoom_input_name, zoom_input_uuid)

	filename = os.path.abspath(zoom_input_name + ".png")
	finder = BoxFinder()

	prev_coords = None
	count = 0
	while True:
		start = time()
		print("Getting snapshot...")
		response = obs.request("SaveSourceScreenshot", {
			"sourceUuid": zoom_input_uuid,
			"imageFormat": "png",
			"imageFilePath": filename,
			})
		print("Elapsed:", time() - start)

		finder.load_image(filename)
		coords = finder.find_box()
		print("Elapsed:", time() - start)

		if coords is None:
			print("No box")
		elif coords == prev_coords:
			print("No change")
		else:
			#finder.draw_box(*coords)
			#finder.show()

			set_zoom_crop(finder, zoom0, coords)

			set_zoom_crop(finder, zoom1 if (count % 2) == 0 else zoom2, coords)

			prev_coords = coords
			count += 1
			print("Elapsed:", time() - start)

		sleep(5)

def get_zoom_cropper(scene_name, zoom_input_name, zoom_input_uuid):
	scene_uuid = obs.get_scene_uuid(scene_name)
	if scene_uuid is None:
		scene_uuid = obs.create_scene(scene_name)["sceneUuid"]

	scene_item_id = obs.get_scene_item_id(scene_uuid, zoom_input_name)
	if scene_item_id is None:
		scene_item_id = obs.create_scene_item(scene_uuid=scene_uuid, source_uuid=zoom_input_uuid)

	return scene_uuid, scene_item_id

def set_zoom_crop(finder, zoom_crop, coords):
	scene_uuid, scene_item_id = zoom_crop
	x1, y1, x2, y2 = coords
	obs.scale_scene_item(scene_uuid, scene_item_id, {
		"cropLeft": x1,
		"cropTop": y1,
		"cropRight": finder.img.width - x2,
		"cropBottom": finder.img.height - y2,
		})

#
# https://pillow.readthedocs.io/en/stable/index.html
# https://realpython.com/image-processing-with-the-python-pillow-library/
# https://github.com/python-pillow/Pillow
#
class BoxFinder:
	border_color = pack("BBBB", 35, 217, 89, 255)		# green
	bytes_per_pixel = len(border_color)
	border_color_run = 50 * border_color
	corner_radius = 16

	def load_image(self, filename):
		self.img = img = Image.open(filename)
		print(img.format, img.width, img.height, img.mode)

	def find_box(self):
		data = self.img.tobytes()
		row_length_in_bytes = self.img.width * self.bytes_per_pixel

		try:
			hit1 = data.index(self.border_color_run)
		except ValueError:
			return None
		x1 = hit1 % row_length_in_bytes / self.bytes_per_pixel 
		y1 = int(hit1 / row_length_in_bytes)
		print(x1, y1)
		x1 -= self.corner_radius

		try:
			hit2 = data.index(self.border_color_run, hit1 + 50 * row_length_in_bytes)
		except ValueError:
			return None
		x2 = hit2 % row_length_in_bytes / self.bytes_per_pixel 
		y2 = int(hit2 / row_length_in_bytes)
		print(x2, y2)
		#x2 -= self.corner_radius
		x2 = x1
		y2 += 4		# shift down to bottom of border

		#frame_width = int((y2 - y1) * 16 / 8.85)
		frame_width = int((y2 - y1) * 16 / 9)
		x2 += frame_width

		print(self.img.width - x2, self.img.height - y2)

		return x1, y1, x2, y2

	def draw_box(self, x1, y1, x2, y2):
		draw = ImageDraw.Draw(self.img)
		draw.rectangle(((x1, y1), (x2, y2)), outline=(255, 0, 0), width=2)

	def show(self):
		self.img.show()

