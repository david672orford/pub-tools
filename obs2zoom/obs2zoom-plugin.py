import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import obspython as obs
import threading
import logging, logging.config

from obs_api import ObsEventReader
from obs2zoom_policies import ObsToZoomManual, ObsToZoomAuto
from zoom import ZoomControl

# We control logging levels in the following way:
# * The Debug checkbox changes the logging level of the console handler
# * The level set on the "root" logger is the default for children 
# * The level of specific children can be set by added lines to "loggers"
logging.config.dictConfig({
	'version': 1,
	'formatters': {
		'default': {
			'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
			'datefmt': '%H:%M:%S',
			}
		},
	'handlers': {
		'console': {
			'class': 'logging.StreamHandler',
			'formatter': 'default',
			},
		'file': {
			'class': 'logging.FileHandler',
			'filename': '/tmp/obs2zoom.log',
			'formatter': 'default',
			'level': 'DEBUG',
			},
		},
	'root': {
		'level': 'DEBUG',
		'handlers': ['console'],
		},
	'loggers': {
		}
	})

# Show levels settings of all the loggers
for logger_name, logger in logging.root.manager.loggerDict.items():
	print("Logger", logger_name, logging.getLevelName(getattr(logger, "level", None)))

class MyObsScript:
	description = "Start and stop sharing of virtual camera in Zoom"

	def __init__(self):
		self.mode = 0
		self.debug = None
		self.obs_reader = None
		self.zoom_controller = None
		self.policy = None
		self.thread = None

		# Get the log handler of the root logger so that we can change its level
		self.log_handler = logging.getLogger().handlers[0]

		# This is the logger to which this class will log
		self.logger = logging.getLogger(__name__)

		# Create global hooks which will be called by OBS-Studio which connect
		# our our methods. They are called in the order listed here except it
		# is unclear when script_save() is called.
		g = globals()
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
				self.log_handler.setLevel(logging.DEBUG)
				self.logger.debug("log_level set to DEBUG")
			else:
				if self.log_handler.level != logging.NOTSET:
					self.logger.debug("log_level set to WARN")
				self.log_handler.setLevel(logging.WARN)
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
			self.logger.info("Event reader thread stopped.")
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
		self.logger.debug("Thread body")
		while self.policy.handle_message():
			pass
		self.logger.debug("Thread exiting")

MyObsScript()

