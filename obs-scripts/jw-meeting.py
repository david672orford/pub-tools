# OBS Studio Plugin which embeds the Flask web server

import obspython as obs
import threading
import logging
from urllib.request import urlopen
from werkzeug.serving import make_server, WSGIRequestHandler
from app.werkzeug_logging import MyWSGIRequestHandler

from app import app

logging.basicConfig(
	level=logging.DEBUG,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)

class MyObsScript:
	description = "Load videos and illustrations from JW.ORG"

	def __init__(self):
		self.enable = False		# should the HTTP server be running?
		self.debug = None
		self.thread = None		# HTTP server thread

		# This is the logger to which this class will log
		self.logger = logging.getLogger("app")

		g = globals()
		g['script_defaults'] = lambda settings: self.script_defaults(settings)
		g['script_description'] = lambda: self.description
		g['script_update'] = lambda settings: self.script_update(settings)
		g['script_properties'] = lambda: self.script_properties()
		g['script_unload'] = lambda: self.script_unload()

	# Settings screen defaults
	def script_defaults(self, settings):
		obs.obs_data_set_default_bool(settings, "enable", False)
		obs.obs_data_set_default_bool(settings, "debug", False)

	# Settings screen widgets
	def script_properties(self):
		props = obs.obs_properties_create()
		obs.obs_properties_add_bool(props, "enable", "Enable")
		obs.obs_properties_add_bool(props, "debug", "Debug")
		return props

	# Accept settings (possibly changed)
	def script_update(self, settings):
		enable = obs.obs_data_get_bool(settings, "enable")
		debug = obs.obs_data_get_bool(settings, "debug")
		#self.logger.debug("Settings: enable=%s, debug=%s", enable, debug)

		if debug != self.debug:
			if debug:
				self.logger.setLevel(logging.DEBUG)
				self.logger.debug("log_level set to DEBUG")
			else:
				if self.logger.level != logging.NOTSET:
					self.logger.debug("log_level set to WARN")
				self.logger.setLevel(logging.WARN)
			self.debug = debug

		if enable != self.enable:
			self.logger.debug("enable changed from %s to %s", self.enable, enable)
			self.enable = enable
			self.update_thread()

	# Shutdown
	def script_unload(self):
		self.enable = False
		self.update_thread()

	# Start or stop the HTTP server thread in accord with the current settings
	def update_thread(self):
		self.logger.debug("update_thread(): enable=%s thread=%s", self.enable, self.thread)

		if self.thread is not None:
			self.logger.info("Stopping HTTP server...")
			try:
				urlopen('http://127.0.0.1:5000/obs/shutdown')
			except Exception as e:
				self.logger.debug("urlopen(): %s" % str(e))
			self.thread.join()
			self.thread = None
			self.logger.info("HTTP server stopped.")

		if self.enable:
			self.logger.debug("Starting server...")
			server = make_server(host="127.0.0.1", port=5000, app=app, request_handler=MyWSGIRequestHandler)
			self.thread = threading.Thread(target=server.serve_forever)
			self.thread.daemon = True
			self.thread.start()
			self.logger.debug("Server is running.")

MyObsScript()
