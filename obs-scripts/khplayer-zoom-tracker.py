"""Do screen capture on Zoom"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from venv_tool import activate
activate()

from time import sleep, time
from ctypes import string_at, byref
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

	def __init__(self, *args, debug=False, **kwargs):
		super().__init__(*args, **kwargs)
		self.source_name = "Zoom Capture"
		self.cropper_names = (
			"Zoom Crop 0",
			"Zoom Crop 1",
			"Zoom Crop 2",
			)
		self.capture = None
		self.tracker = ZoomTracker(debug=self.debug)
		self.croppers = []
		self.last_active = False
		self.last_snapshot = False

		self.gui = [
			ObsWidget("select", "capture_window", "Zoom Window",
				value=lambda: self.capture.get_window(),
				options=lambda: self.capture.get_window_options(),
				),
			]

	def on_finished_loading(self):
		"""Create the Zoom scenes an sources if they do not exist yet"""

		# Create the input which captures the main Zoom screen, or reuse the old one if it exists.
		self.capture = WindowCapture(self.source_name)

		# Create the sources which will contain cropped versions of this input
		for i in range(len(self.cropper_names)):
			cropper_name = self.cropper_names[i]
			if self.debug:
				print("Creating cropper:", cropper_name)
			self.croppers.append(ZoomCropper(cropper_name, self.source_name, self.capture.source, i!=0))
			# FIXME: Needed to prevent lockup when more than one needs to be created
			sleep(.1)

	def on_gui_change(self, settings):
		"""When a setting is changed in the GUI"""
		if self.debug:
			print("GUI change: capture_window is now:", settings.capture_window)
		self.capture.set_window(settings.capture_window)

	def on_unload(self):
		"""Script or OBS shutting down. Free resources."""
		if self.capture is not None:
			self.capture.destroy()
			self.capture = None
		for zoom_scene in self.croppers:
			zoom_scene.release()

	def active(self):
		"""Is at least one OBS scene showing Zoom active?"""
		#return obs.obs_source_active(self.capture.source)
		for cropper in self.croppers:
			if obs.obs_source_active(cropper.source):
				return True
		return False

	def tick(self):
		"""Time to get a screenshot and adjust the cropping"""
		if self.active():
			if not self.last_active:
				if self.debug:
					print("Zoom scene now active")
				self.last_active = True
			data, width, height = snapshot(self.capture.source)
			if data is not None:
				if not self.last_snapshot:
					if self.debug:
						print("Zoom snapshot gained")
					self.last_snapshot = True
				def task():
					obs.remove_current_callback()
					img = Image.frombuffer("RGBA", (width, height), data, "raw", "RGBA", 0, 1)
					img = img.convert("RGB")
					#img.save("/tmp/image.png", "PNG")
					self.tracker.load_image(img)
					self.tracker.do_cropping(self.croppers)
				obs.timer_add(task, 1)
			elif self.last_snapshot:
				if self.debug:
					print("Zoom snapshot lost")
				self.last_snapshot = False
		elif self.last_active is True:
			if self.debug:
				print("Zoom scene now inactive")
			self.last_active = False

class WindowCapture:
	"""Wrapper for an OBS input which does screen capture on an application window"""
	def __init__(self, source_name):
		self.source = obs.obs_get_source_by_name(source_name)
		if sys.platform == "win32":
			self.input_kind = "window_capture"
			self.window_key = "window"
		else:
			self.input_kind = "xcomposite_input"
			self.window_key = "capture_window"
		if self.source is None:
			self.source = obs.obs_source_create(self.input_kind, source_name, None, None)
		source_settings = obs.obs_data_create()
		if sys.platform == "win32":
			obs.obs_data_set_bool(source_settings, "cursor", False)
			obs.obs_data_set_int(source_settings, "priority", 1)	# Window title must match
			obs.obs_data_set_int(source_settings, "method", 2)		# Windows 10 (1903 and up)
		else:
			obs.obs_data_set_bool(source_settings, "show_cursor", False)
		obs.obs_source_update(self.source, source_settings)
		obs.obs_data_release(source_settings)

	def destroy(self):
		obs.obs_source_release(self.source)

	def get_window(self):
		source_settings = obs.obs_source_get_settings(self.source)
		value = obs.obs_data_get_string(source_settings, self.window_key)
		obs.obs_data_release(source_settings)
		print("============", value, "============")
		return value

	def set_window(self, window):
		source_settings = obs.obs_data_create()
		obs.obs_data_set_string(source_settings, self.window_key, window)
		obs.obs_source_update(self.source, source_settings)
		obs.obs_data_release(source_settings)

	def get_window_options(self):
		properties = obs.obs_get_source_properties(self.input_kind)
		property = obs.obs_properties_get(properties, self.window_key)
		capture_windows = []
		for i in range(obs.obs_property_list_item_count(property)):
			option = obs.obs_property_list_item_string(property, i)
			capture_windows.append((option, option.split("\r\n")[1]))
		obs.obs_properties_destroy(properties)
		return capture_windows

def snapshot(source):
	"""Take a screenshot of the supplied OBS source"""
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
			#data = bytes(rawdata[:linesize*height])
			data = bytearray(string_at(rawdata, linesize*height))
			obs.gs_stagesurface_unmap(stagesurf)

		obs.gs_stagesurface_destroy(stagesurf)
	obs.gs_texrender_destroy(texrender)

	obs.obs_leave_graphics()

	if data is None:
		return None, None, None
	return data, width, height

class ZoomCropper:
	"""
	Wrapper for an OBS scene which contains a cropped version of the Zoom screen capture
	There is an OBS-Websocket version of this in cli_zoom.py.
	"""

	def __init__(self, source_name, zoom_source_name, zoom_source, toggle):
		self.prev_crop_box = None
		self.toggle = toggle

		# Find the named scene. Create it if it does not exist.
		self.source = obs.obs_get_source_by_name(source_name)
		if self.source is None:
			self.source = obs.obs_source_create("group", source_name, None, None)

		# If the named source is not in the scene, add it.
		group = obs.obs_group_from_source(self.source)
		self.scene_item = obs.obs_scene_find_source(group, zoom_source_name)
		if self.scene_item is None:
			self.scene_item = obs.obs_scene_add(group, zoom_source)

		# Prepare the scene item for cropping.
		obs.obs_sceneitem_set_bounds_type(self.scene_item, obs.OBS_BOUNDS_SCALE_INNER)
		bounds = obs.vec2()
		bounds.x = 1280
		bounds.y = 720
		obs.obs_sceneitem_set_bounds(self.scene_item, bounds)
		obs.obs_sceneitem_set_bounds_alignment(self.scene_item, 0)

	def release(self):
		obs.obs_source_release(self.source)

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

zoom_tracker = ObsZoomTracker(debug=True)

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
