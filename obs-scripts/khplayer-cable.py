import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from obs_wrap import ObsScript, ObsWidget
from app import create_app
from app.subapps.khplayer.utils.virtual_cable import patchbay, connect_all, destroy_cable
from app.subapps.khplayer.utils.config_editor import config_update_dict

class ObsVirtualAudioCable(ObsScript):
	description = "Create virtual audio cable in the Pipewire audio server to connect OBS, Zoom, a microphone, and speakers."

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.app = create_app()
		config = self.app.config.get("PERIPHERALS",{})

		# Define script configuration GUI
		self.settings_widgets = [
			ObsWidget("select", "microphone", "Microphone", value=lambda: config.get("microphone"), options=self.get_microphones),
			ObsWidget("select", "speakers", "Loadspeakers", value=lambda: config.get("speakers"), options=self.get_speakers),
			ObsWidget("button", "reconnect", "Reconnect Audio", callback=self.on_button),
			]

	def get_microphones(self):
		patchbay.load()
		microphones = []
		for node in patchbay.nodes:
			if node.media_class == "Audio/Source":
				microphones.append((node.name, node.nick if node.nick else node.name))
		return microphones

	def get_speakers(self):
		#patchbay.load()		# already loaded
		speakers = []
		for node in patchbay.nodes:
			if node.media_class == "Audio/Sink" and node.name != "To-Zoom":
				speakers.append((node.name, node.nick if node.nick else node.name))
		return speakers

	def on_button(self):
		print("button pressed")

	# Accept settings from the script configuration GUI
	def on_settings(self, settings):
		with self.app.app_context():
			config_update_dict("PERIPHERALS", {
				"microphone": settings.microphone,
				"speakers": settings.speakers,
				})

	def on_load(self):
		patchbay.load()
		connect_all(patchbay, self.app.config["PERIPHERALS"])

	def on_unload(self):
		patchbay.load()
		destroy_cable(patchbay)

ObsVirtualAudioCable(debug=True)
