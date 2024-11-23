import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obs_wrap import ObsScript, ObsWidget
from config import get_config, put_config
from app.subapps.khplayer.utils.virtual_cable import patchbay, connect_all, destroy_cable

class ObsVirtualAudioCable(ObsScript):
	description = """
		<h2>KH Player—Virtual Audio Cable</h2>
		<p>Create virtual audio cable in the Pipewire audio server to connect OBS, Zoom, a microphone, and speakers.</p>
		"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.config = None
		self.microphone_options = []
		self.speakers_options = []	

		# Define script configuration GUI
		self.gui = [
			ObsWidget("select", "microphone", "Microphone",
				value=lambda: self.config.get("microphone"),
				options=lambda: self.microphone_options,
				),
			ObsWidget("select", "speakers", "Loadspeakers",
				value=lambda: self.config.get("speakers"),
				options=lambda: self.speakers_options,
				),
			ObsWidget("button", "reconnect", "Reconnect Audio", callback=self.on_button),
			]

	def on_load(self, settings):
		self.config = get_config("PERIPHERALS")
		if self.debug:
			print("config:", self.config)
		patchbay.load()
		connect_all(patchbay, self.config)
		#obs.obs_frontend_add_tools_menu_item("Reconnect Audio", self.on_button)

	# About to display the GUI
	def on_before_gui(self):
		self.config = get_config("PERIPHERALS")
		if self.debug:
			print("on_gui()", self.config)
		patchbay.load()
		self.microphone_options = []
		self.speakers_options = []	
		for node in patchbay.nodes:
			if node.media_class == "Audio/Source":
				self.microphone_options.append((node.name, node.nick if node.nick else node.name))
			if node.media_class == "Audio/Sink" and node.name != "To-Zoom":
				self.speakers_options.append((node.name, node.nick if node.nick else node.name))

	# Accept settings from the script configuration GUI
	def on_gui_change(self, settings):
		print("settings:", settings)
		self.config["microphone"] = settings.microphone
		self.config["speakers"] = settings.speakers

	def on_button(self):
		print("Reconnect Audio")
		put_config("PERIPHERALS", self.config)
		patchbay.load()
		connect_all(patchbay, self.config)

	def on_unload(self):
		patchbay.load()
		destroy_cable(patchbay)

ObsVirtualAudioCable(debug=False)
