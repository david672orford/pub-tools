"""Use window capture on Zoom to get video of individual participants"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from venv_tool import activate
activate()

from time import sleep, time
from ctypes import string_at, byref
from subprocess import run

from PIL import Image
import obspython as obs

import gs_stagesurface_map
from obs_wrap import ObsScript, ObsWidget
from app.subapps.khplayer.utils.zoom_tracker import ZoomTracker

class ObsZoomTracker(ObsScript):
	"""
	<h2>KH Player—Zoom Tracker</h2>
	<p>Run screen capture on the main Zoom window and create sources which track the current and last two speakers.</p>
	"""
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.paused = True
		self.source_name = "Zoom Capture"
		self.cropper_names = (
			"Zoom Participant 0",
			"Zoom Participant 1",
			"Zoom Participant 2",
			)
		self.capture = None
		self.tracker = ZoomTracker(debug=self.debug)
		self.croppers = []
		self.last_showing = False
		self.last_snapshot = False

		# External Python script which presses the unspotlight button in Zoom
		if sys.platform == "linux":
			self.zoom_unspotlight = os.path.join(os.path.dirname(__file__), ".libs", "zoom-unspotlight.py")
		else:
			self.zoom_unspotlight = None

		self.gui = [
			ObsWidget("select", "capture_window", "Zoom Window",
				value=lambda: self.capture.get_window(),
				options=lambda: self.capture.get_window_options(),
				),
			ObsWidget("bool", "paused", "Pause Tracking", default_value=False),
			ObsWidget("bool", "exclude_first_box", "Exclude First Box", default_value=True),
			ObsWidget("bool", "debug", "Debug", default_value=False),
			]

	def on_finished_loading(self):
		"""Create the Zoom capture source and participant sources, if they do not exist yet"""

		# Create the input which captures the main Zoom screen, or reuse the old one if it exists.
		self.capture = WindowCapture(self.source_name)

		# Create the sources which will contain cropped versions of this input
		for i in range(len(self.cropper_names)):
			cropper_name = self.cropper_names[i]
			if self.debug:
				print("Creating cropper:", cropper_name)
			self.croppers.append(ZoomCropper(cropper_name, self.source_name, self.capture.source))
			# FIXME: Needed to prevent lockup when more than one needs to be created
			sleep(.1)

	def on_gui_change(self, settings):
		"""When a setting is changed in the GUI"""
		if self.debug:
			print("GUI change:", settings)
		self.capture.set_window(settings.capture_window)
		self.paused = settings.paused
		self.tracker.set_exclude_first_box(settings.exclude_first_box)
		self.debug = settings.debug
		self.tracker.debug = settings.debug

	def on_unload(self):
		"""Script or OBS shutting down. Free resources."""
		if self.capture is not None:
			self.capture.destroy()
			self.capture = None
		for zoom_scene in self.croppers:
			zoom_scene.release()

	def track(self):
		"""Time to get a screenshot and adjust the cropping"""
		if self.paused:
			return
		if self.capture is not None and obs.obs_source_showing(self.capture.source):
			if not self.last_showing:
				if self.debug:
					print("Zoom source now showing")
				self.last_showing = True
				if self.zoom_unspotlight is not None:
					run(self.zoom_unspotlight)
			data, width, height = self.capture.snapshot()
			if data is not None:
				if not self.last_snapshot:
					if self.debug:
						print("Zoom snapshotting gained")
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
					print("Zoom snapshotting lost")
				self.last_snapshot = False
		elif self.last_showing is True:
			if self.debug:
				print("Zoom sources no longer showing")
			self.tracker.reset_speakers()
			self.tracker.do_cropping(self.croppers)
			self.last_showing = False

class WindowCapture:
	"""Wrapper for an OBS input which does screen capture on an application window"""

	def __init__(self, source_name):
		if sys.platform == "win32":
			self.input_kind = "window_capture"
			self.window_key = "window"
			self.cursor_key = "cursor"
		else:
			self.input_kind = "xcomposite_input"
			self.window_key = "capture_window"
			self.cursor_key = "show_cursor"
		self.source = obs.obs_get_source_by_name(source_name)
		if self.source is None:
			self.source = obs.obs_source_create(self.input_kind, source_name, None, None)
		source_settings = obs.obs_data_create()
		obs.obs_data_set_bool(source_settings, self.cursor_key, False)
		if sys.platform == "win32":
			obs.obs_data_set_int(source_settings, "priority", 1)	# Window title must match
			obs.obs_data_set_int(source_settings, "method", 2)		# Windows 10 (1903 and up)
		obs.obs_source_update(self.source, source_settings)
		obs.obs_data_release(source_settings)

	def destroy(self):
		obs.obs_source_release(self.source)
		self.source = None

	def get_window(self):
		"""Get window currently being captured"""
		source_settings = obs.obs_source_get_settings(self.source)
		value = obs.obs_data_get_string(source_settings, self.window_key)
		obs.obs_data_release(source_settings)
		return value

	def set_window(self, window):
		"""Set the window to be captured"""
		source_settings = obs.obs_data_create()
		obs.obs_data_set_string(source_settings, self.window_key, window)
		obs.obs_source_update(self.source, source_settings)
		obs.obs_data_release(source_settings)

	def get_window_options(self):
		"""Get the list of windows available for capturing"""
		properties = obs.obs_get_source_properties(self.input_kind)
		property = obs.obs_properties_get(properties, self.window_key)
		current_value = self.get_window()
		current_name = current_value.split("\r\n")[1] if "\r\n" in current_value else current_value
		current_value_found = False
		available_windows = []
		for i in range(obs.obs_property_list_item_count(property)):
			option_name = obs.obs_property_list_item_name(property, i)
			option_value = obs.obs_property_list_item_string(property, i)
			available_windows.append((option_value, option_name))
			if option_value == current_value:
				current_value_found = True
		obs.obs_properties_destroy(properties)
		if not current_value_found:
			available_windows.insert(0, (current_value, current_name))
		return available_windows

	def snapshot(self):
		"""Take a screenshot of the supplied OBS source"""
		# We found these examples helpful:
		# https://github.com/obsproject/obs-websocket/blob/master/src/requesthandler/RequestHandler_Sources.cpp
		# https://obsproject.com/forum/threads/tips-and-tricks-for-lua-scripts.132256/page-2#post-515653

		obs.obs_enter_graphics()

		source = self.source
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
	Wrapper for a proxy source which crops a piece out of Zoom Capture.
	"""
	def __init__(self, source_name, zoom_source_name, zoom_source):
		self.source_name = source_name
		self.prev_crop_box = None
		# Find the named source. Create it if it does not exist.
		self.source = obs.obs_get_source_by_name(source_name)
		if self.source is None:
			self.source = obs.obs_source_create("khplayer-zoom-participant", source_name, None, None)
		handler = obs.obs_source_get_signal_handler(self.source)

	def release(self):
		obs.obs_source_release(self.source)
		self.source = None

	def set_crop(self, crop_box):
		if crop_box != self.prev_crop_box:
			source_settings = obs.obs_data_create()
			if crop_box is False:
				obs.obs_data_set_bool(source_settings, "enabled", False)
			else:
				if self.prev_crop_box in (None, False):
					obs.obs_data_set_bool(source_settings, "enabled", True)
				obs.obs_data_set_int(source_settings, "crop_x", crop_box.x)
				obs.obs_data_set_int(source_settings, "crop_y", crop_box.y)
				obs.obs_data_set_int(source_settings, "crop_width", crop_box.width)
				obs.obs_data_set_int(source_settings, "crop_height", crop_box.height)
			obs.obs_source_update(self.source, source_settings)
			obs.obs_data_release(source_settings)
			self.prev_crop_box = crop_box

zoom_tracker = ObsZoomTracker()

# The OBS documentation recommends against using this function, but if we
# use a timer as the recommend, OBS segfaults in the graphics thread.
tick_count = 0
def script_tick(seconds):
	global tick_count
	SCREENSHOT_INTERVAL = 15
	if seconds > 0.034:
		print("long tick:", seconds)
	tick_count += 1
	if tick_count > SCREENSHOT_INTERVAL:
		zoom_tracker.track()
		tick_count = 0
