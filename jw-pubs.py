# OBS Studio Plugin which embeds the Flask web server

import obspython as obs
import threading
import logging
from werkzeug.serving import make_server
from urllib.request import urlopen

from app import app

logging.basicConfig(
	level=logging.WARN,
	format='%(asctime)s %(levelname)s %(message)s',
	datefmt='%Y-%m-%d %H:%M:%S'
	)

logger = logging.getLogger(__name__)
#logger.setLevel(logging.DEBUG)

class MyObsScript:
	description = "Load videos and illustrations from JW.ORG"

	def __init__(self):
		g = globals()
		g['script_defaults'] = lambda settings: self.script_defaults(settings)
		g['script_description'] = lambda: self.description
		g['script_update'] = lambda settings: self.script_update(settings)
		g['script_properties'] = lambda: self.script_properties()
		g['script_unload'] = lambda: self.script_unload()

		self.enable = False
		self.thread = None
		self.server = None

	def script_defaults(self, settings):
		obs.obs_data_set_default_bool(settings, "enable", False)

	def script_update(self, settings):
		self.enable = obs.obs_data_get_bool(settings, "enable")
		self.update_thread()

	def script_properties(self):
		props = obs.obs_properties_create()
		obs.obs_properties_add_bool(props, "enable", "Enable")
		return props

	def script_unload(self):
		self.enable = False
		self.update_thread()

	def update_thread(self):
		logger.debug("update_thread(): %s %s", self.enable, self.thread)

		if self.thread is not None:
			logger.debug("Stopping server...")
			try:
				urlopen('http://127.0.0.1:5000/obs/shutdown')
			except Exception as e:
				logger.debug("urlopen(): %s" % str(e))
			logger.debug("Stopping thread...")
			self.thread.join()
			logger.debug("Thread stopped.")
			self.thread = None
			self.server = None

		if self.enable:
			logger.debug("Starting server...")
			self.server = make_server("127.0.0.1", 5000, app)
			self.thread = threading.Thread(target=lambda: self.thread_body())
			self.thread.daemon = True
			self.thread.start()

	def thread_body(self):
		logger.debug("Server thread started.")
		self.server.serve_forever()
		logger.debug("Server thread exiting.")

MyObsScript()
