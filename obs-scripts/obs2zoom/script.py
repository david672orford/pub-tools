import obspython as obs
import threading
import logging

from obs2zoom.obs_api import ObsEventReader
from obs2zoom.policies import ObsToZoomManual, ObsToZoomAuto
from obs2zoom.zoom import ZoomControl

class MyObsScript:
	description = "Start and stop sharing of virtual camera in Zoom"

	def __init__(self, g):
		self.mode = 0
		self.debug = None
		self.obs_reader = None
		self.zoom_controller = None
		self.policy = None
		self.thread = None

		# This is the logger to which this class will log
		self.logger = logging.getLogger("obs2zoom")

		# Create global hooks which will be called by OBS-Studio which connect
		# our our methods. They are called in the order listed here except it
		# is unclear when script_save() is called.
		#g = globals()
		g['script_defaults'] = lambda settings: self.script_defaults(settings)
		g['script_description'] = lambda: self.description
		g['script_update'] = lambda settings: self.script_update(settings)
		g['script_properties'] = lambda: self.script_properties()
		g['script_unload'] = lambda: self.script_unload()

	# Settings screen defaults
	def script_defaults(self, settings):
		obs.obs_data_set_default_int(settings, "mode", 0)
		obs.obs_data_set_default_bool(settings, "debug", False)

	# Settings screen widgets
	def script_properties(self):
		props = obs.obs_properties_create()
		p = obs.obs_properties_add_list(props, "mode", "Mode", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
		obs.obs_property_list_insert_int(p, 0, "Off", 0)
		obs.obs_property_list_insert_int(p, 1, "Manual", 1)
		obs.obs_property_list_insert_int(p, 2, "When Playing", 2)
		obs.obs_properties_add_bool(props, "debug", "Debug")
		return props

	# Accept settings (possibly changed)
	def script_update(self, settings):
		mode = obs.obs_data_get_int(settings, "mode")
		debug = obs.obs_data_get_bool(settings, "debug")
		#self.logger.debug("Settings: mode=%s, debug=%s", mode, debug)

		if debug != self.debug:
			if debug:
				self.logger.setLevel(logging.DEBUG)
				self.logger.debug("log_level set to DEBUG")
			else:
				if self.logger.level != logging.NOTSET:
					self.logger.debug("log_level set to WARN")
				self.logger.setLevel(logging.WARN)
			self.debug = debug

		if mode != self.mode:
			self.mode = mode
			self.update_thread()

	# Shutdown
	def script_unload(self):
		self.mode = 0
		self.update_thread()

	# Start or stop event reader thread in accord with the current settings
	def update_thread(self):
		self.logger.debug("update_thread(): mode=%s thread=%s", self.mode, self.thread)

		if self.thread is not None:
			self.logger.info("Stopping event reader thread...")
			self.obs_reader.shutdown()
			self.thread.join()
			self.thread = None

		if self.mode > 0:
			if self.obs_reader is None:
				self.obs_reader = ObsEventReader()
				self.zoom_controller = ZoomControl()
			self.obs_reader.startup()

			if self.mode == 1:
				self.policy = ObsToZoomManual(self.obs_reader, self.zoom_controller)
			else:
				self.policy = ObsToZoomAuto(self.obs_reader, self.zoom_controller)

			self.thread = threading.Thread(target=self.thread_body)
			self.thread.daemon = True
			self.thread.start()

	# Read OBS events and start and stop screen sharing in Zoom as needed.
	def thread_body(self):
		self.logger.debug("Event reader thread started.")
		while self.policy.handle_message():
			pass
		self.logger.debug("Event reader thread exiting.")
