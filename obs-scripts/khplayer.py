# OBS Studio Plugin which embeds the Flask web server to run
# the same apps as ../start.py does.

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import obspython as obs
from threading import Thread
from werkzeug.serving import make_server
import logging

from app.utils.clean_logs import CleanlogWSGIRequestHandler
from app import create_app

logging.basicConfig(
	level=logging.WARN,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S'
	)
#logging.getLogger("app").addHandler(logging.FileHandler("/tmp/khplayer.log"))

class KHPlayerScript:
	description = "Load videos and illustrations from JW.ORG"

	def __init__(self):
		self.enable = False		# should the HTTP server be running?
		self.debug = None

		self.app = create_app()
		self.thread = None		# HTTP server thread
		self.server = None		# HTTP server object

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
			self.server.shutdown()
			self.thread.join()
			self.thread = None
			self.server = None
			self.logger.info("HTTP server stopped.")

		if self.enable:
			self.logger.debug("Starting server...")
			#listen_address = "127.0.0.1"
			listen_address = "0.0.0.0"
			listen_port = 5000
			self.server = make_server(listen_address, port=listen_port, app=self.app, request_handler=CleanlogWSGIRequestHandler, threaded=True)
			self.thread = Thread(target=lambda: self.server.serve_forever())
			self.thread.daemon = True
			self.thread.start()
			self.logger.debug("Server is running.")

KHPlayerScript()

