"""Do screen capture on Zoom"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from time import sleep
from PIL import Image
import obspython as obs
import gs_stagesurface_map
from obs_wrap import ObsScript, ObsWidget
from app.subapps.khplayer.utils.zoom_tracker import ZoomTracker

class ObsZoomTracker(ObsScript):
	"""
	<h2>KH Player—Zoom Tracker</h2>
	<p>Run screen capture on the main Zoom window and crop out the current and previous speakers.</p>
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.windows = []
		self.source_name = "Zoom Capture"
		self.source = None
		self.scene_names = (
			"* Zoom Speaker",
			"* Zoom 1",
			"* Zoom 2",
			)
		self.zoom_scenes = []
		self.tracker = ZoomTracker()

		self.gui = [
			ObsWidget("select", "capture_window", "Zoom Window",
				options=lambda: self.capture_windows,
				),
			]

	def on_finished_loading(self):
		"""Create the Zoom scenes an sources if they do not exist yet"""

		# Create the input which captures the main Zoom screen
		self.source = obs.obs_get_source_by_name(self.source_name)
		if self.source is None:
			self.source = obs.obs_source_create("xcomposite_input", self.source_name, None, None)

		# Create the scenes which will contain cropped versions of this input
		for i in range(len(self.scene_names)):
			scene_name = self.scene_names[i]
			print("Creating", scene_name)
			self.zoom_scenes.append(ZoomCropper(scene_name, self.source_name, self.source, i!=0))
			# FIXME: Needed to prevent lockup when more than one needs to be created
			sleep(.1)

	def on_before_gui(self):
		"""Load values and options into the GUI before it is displayed"""
		self.capture_windows = []
		properties = obs.obs_get_source_properties("xcomposite_input")
		property = obs.obs_properties_get(properties, "capture_window")
		for i in range(obs.obs_property_list_item_count(property)):
			option = obs.obs_property_list_item_string(property, i)
			self.capture_windows.append((option, option.split("\r\n")[1]))
		obs.obs_properties_destroy(properties)

	def on_gui_change(self, settings):
		"""When a setting is changed in the GUI"""
		print("GUI change: capture_window:", settings.capture_window)
		source_settings = obs.obs_data_create()
		obs.obs_data_set_string(source_settings, "capture_window", settings.capture_window)
		obs.obs_data_set_int(source_settings, "cut_top", 130)
		obs.obs_data_set_int(source_settings, "cut_bot", 0)
		obs.obs_data_set_bool(source_settings, "show_cursor", False)
		obs.obs_source_update(self.source, source_settings)
		obs.obs_data_release(source_settings)

	def on_unload(self):
		if self.source is not None:
			obs.obs_source_release(self.source)

	def on_source_show(self):
		print("Source is now showing")
		self.schedule_tracking(100, repeat=True)

	def tick(self):
		if obs.obs_source_active(self.source):
			img = snapshot(self.source)
			if img is not None:
				#img.save("/tmp/image.png", "PNG")
				self.tracker.load_image(img)
				self.tracker.do_cropping(self.zoom_scenes)

def snapshot(source):
	"""Take a screenshot of the named source and return it as a PIL image"""
	# We found these examples helpful:
	# https://github.com/obsproject/obs-websocket/blob/master/src/requesthandler/RequestHandler_Sources.cpp
	# https://obsproject.com/forum/threads/tips-and-tricks-for-lua-scripts.132256/page-2#post-515653

	obs.obs_enter_graphics()

	width = obs.obs_source_get_width(source)
	height = obs.obs_source_get_height(source)

	# Render the video frame, first in video RAM
	data = None
	texrender = obs.gs_texrender_create(obs.GS_RGBA, obs.GS_ZS_NONE)
	if obs.gs_texrender_begin(texrender, width, height):
		obs.gs_ortho(0.0, float(width), 0.0, float(height), -100.0, 100.0)
		obs.obs_source_video_render(source)
		obs.gs_texrender_end(texrender)

		# Copy the frame from the GPU to system RAM
		stagesurf = obs.gs_stagesurface_create(width, height, obs.GS_RGBA)
		obs.gs_stage_texture(stagesurf, obs.gs_texrender_get_texture(texrender))

		# Get ahold of the copy
		linesize, rawdata = obs.gs_stagesurface_map(stagesurf)
		if linesize is not None:
			data = bytes(rawdata[:linesize*height])
		if data is not None:
			obs.gs_stagesurface_unmap(stagesurf)

		obs.gs_stagesurface_destroy(stagesurf)
	obs.gs_texrender_destroy(texrender)

	obs.obs_leave_graphics()

	if data is None:
		return None

	img = Image.frombuffer("RGBA", (width, height), data, "raw", "RGBA", 0, 1)
	img = img.convert("RGB")
	return img

class ZoomCropper:
	"""
	Wrapper for an OBS scene which contains a cropped version of the Zoom screen capture
	There is an OBS-Websocket version of this in cli_zoom.py.
	"""

	def __init__(self, scene_name, source_name, source, toggle):
		self.prev_crop_box = None
		self.toggle = toggle

		# Find the named scene. Create it if it does not exist.
		scene = obs.obs_get_scene_by_name(scene_name)
		if scene is None:
			scene = obs.obs_scene_create(scene_name)

		# If the named source is not in the scene, add it.
		self.scene_item = obs.obs_scene_find_source(scene, source_name)
		if self.scene_item is None:
			self.scene_item = obs.obs_scene_add(scene, source)

		# Prepare the scene item for cropping.
		obs.obs_sceneitem_set_bounds_type(self.scene_item, obs.OBS_BOUNDS_SCALE_INNER)
		bounds = obs.vec2()
		bounds.x = 1280
		bounds.y = 720
		obs.obs_sceneitem_set_bounds(self.scene_item, bounds)
		obs.obs_sceneitem_set_bounds_alignment(self.scene_item, 0)

		obs.obs_scene_release(scene)

	def set_crop(self, crop_box, width, height):
		if crop_box != self.prev_crop_box:
			if crop_box is False:
				if self.toggle:
					obs.obs_sceneitem_set_visible(self.scene_item, False)
			else:
				if self.prev_crop_box is False:
					obs.obs_sceneitem_set_visible(self.scene_item, True)
				crop_struct = obs.obs_sceneitem_crop()
				crop_struct.left = crop_box.x
				crop_struct.top = crop_box.y
				crop_struct.right = width - crop_box.width - crop_box.x
				crop_struct.bottom = height - crop_box.height - crop_box.y
				obs.obs_sceneitem_set_crop(self.scene_item, crop_struct)
			self.prev_crop_box = crop_box

zoom_tracker = ObsZoomTracker()

# The OBS documentation recommends against using this function, but if we
# use a timer OBS segfaults in the graphics thread.
tick_count = 0
def script_tick(seconds):
	global tick_count
	TICK_DIVISOR = 15
	if seconds > 0.034:
		print("long tick:", seconds)
	tick_count += 1
	if tick_count > TICK_DIVISOR:
		zoom_tracker.tick()
		tick_count = 0
