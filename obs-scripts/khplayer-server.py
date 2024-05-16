# OBS Studio Plugin which embeds the Flask web server to run
# the same apps as ../start.py does.

import os, sys
from threading import Thread
import logging

import obspython as obs
from werkzeug.serving import make_server

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from obs_wrap import ObsScript, ObsWidget
from app.utils.clean_logs import CleanlogWSGIRequestHandler
from app import create_app

logging.basicConfig(
	level=logging.WARN,
	format='%(asctime)s %(levelname)s %(name)s %(message)s',
	datefmt='%H:%M:%S',
	stream=sys.stdout,
	)
#logging.getLogger("app").addHandler(logging.FileHandler("/tmp/khplayer.log"))

# Disable the default handler because it writes to stderr
# which causes OBS to open the script log.
logger = logging.getLogger()
logger.removeHandler(logger.handlers[0])

class KHPlayer(ObsScript):
	"""Run KH Player inside OBS"""

	description = """
		<h2>KH Player—Server</h2>
		<p>KH Player loads videos and illustrations from JW.ORG. Enable it and
		point a browser at <a href="http://127.0.0.1:5000/khplayer/">http://127.0.0.1:5000/khplayer/</a></p>
		"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Define script configuration GUI
		self.gui = [
			ObsWidget("bool", "enable", "Enable Server", default_value=False),
			ObsWidget("bool", "debug", "Debug", default_value=False),
			]

		# Instantiante the KH Player app and prepare to serve it.
		self.app = create_app()
		self.enable = False		# should the HTTP server be running?
		self.debug = False
		self.thread = None		# HTTP server thread
		self.server = None		# HTTP server object
		self.logger = logging.getLogger("app")

	# Accept settings from the script configuration GUI
	def on_gui_change(self, settings):
		if settings.debug != self.debug:
			if settings.debug:
				self.logger.setLevel(logging.DEBUG)
				self.logger.debug("log_level set to DEBUG")
			else:
				if self.logger.level != logging.NOTSET:
					self.logger.debug("log_level set to WARN")
				self.logger.setLevel(logging.WARN)
			self.debug = settings.debug

		if settings.enable != self.enable:
			self.logger.debug("enable changed from %s to %s", self.enable, settings.enable)
			self.enable = settings.enable
			self.apply_server_thread_state()

	# OBS Shutdown
	def on_unload(self):
		self.enable = False
		self.apply_server_thread_state()

	# Start or stop the HTTP server thread in accord with the current settings
	def apply_server_thread_state(self):
		self.logger.debug("apply_server_thread_state(): enable=%s thread=%s", self.enable, self.thread)

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
			try:
				self.server = make_server(
					listen_address, port = listen_port,
					app = self.app,
					request_handler = CleanlogWSGIRequestHandler,
					threaded = True
					)
				self.thread = Thread(target=self.server.serve_forever)
				self.thread.daemon = True
				self.thread.start()
				self.logger.debug("Server is running.")
			except SystemExit:
				self.logger.error("Server failed to start.")

KHPlayer()
