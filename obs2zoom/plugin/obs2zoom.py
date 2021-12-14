import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import obspython as obs
import threading
import logging

logging.basicConfig(
	level=logging.WARN,
	format='%(asctime)s %(levelname)s %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
	)

logger = logging.getLogger(__name__)

from obs_api import ObsEventReader
from obs2zoom_policies import ObsToZoomManual, ObsToZoomAuto
from zoom import ZoomControl

class ObsScriptBase:
	def __init__(self):
		g = globals()
		g['script_defaults'] = lambda settings: self.script_defaults(settings)
		g['script_description'] = lambda: self.script_description()
		g['script_load'] = lambda settings: self.script_load(settings)
		g['script_update'] = lambda settings: self.script_update(settings)
		g['script_properties'] = lambda: self.script_properties()
		g['script_unload'] = lambda: self.script_unload()
		g['script_save'] = lambda settings: self.script_save(settings)

class MyObsScript(ObsScriptBase):
	def __init__(self):
		super().__init__()
		self.obs_reader = None
		self.zoom_controller = None
		self.policy = None
		self.enable = False
		self.mode = None
		self.thread = None

	# Called 1st at script startup to load the default settings
	def script_defaults(self, settings):
		logger.debug("script_defaults(%s)", settings)
		obs.obs_data_set_default_bool(settings, "enable", False)
		obs.obs_data_set_default_int(settings, "mode", 2)

	# Called 2nd at script startup to get the description to display
	# at the top of the scripts settings screen
	def script_description(self):
		logger.debug("script_description()")
		return "Start and stop sharing of virtual camera in Zoom"

	# Called 3rd at script startup
	def script_load(self, settings):
		logger.debug("script_load(%s)", settings)

	# Called 4th at script startup and thereafter whenever settings on the
	# properties page are changed
	def script_update(self, settings):
		logger.debug("script_update(%s)", settings)
		self.enable = obs.obs_data_get_bool(settings, "enable")
		self.mode = obs.obs_data_get_int(settings, "mode")
		self.update_thread()

	# Called whenever the script properties page is to be displayed
	def script_properties(self):
		logger.debug("script_properties()")
		props = obs.obs_properties_create()
		obs.obs_properties_add_bool(props, "enable", "Enable")
		p = obs.obs_properties_add_list(props, "mode", "Mode", obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT)
		obs.obs_property_list_insert_int(p, 0, "Manual", 1)
		obs.obs_property_list_insert_int(p, 1, "When Playing", 2)
		return props

	# Called when the reload button is pressed before executing the callbacks above
	def script_unload(self):
		logger.debug("script_unload()")
		self.enable = False
		self.update_thread()

	# It is not clear when this is called. Calls observed:
	# * when the script throws an exception
	def script_save(self, settings):
		logger.debug("script_save(%s)", settings)

	def update_thread(self):
		logger.debug("update_thread(): %s %s", self.enable, self.thread)

		if self.thread is not None:
			logger.debug("Stopping thread...")
			self.obs_reader.shutdown()
			self.thread.join()
			logger.debug("Thread stopped.")
			self.thread = None

		if self.enable:
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

	def thread_body(self):
		logger.debug("Thread body")
		while self.policy.handle_message():
			pass
		logger.debug("Thread exiting")

MyObsScript()

