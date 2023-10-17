import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.obs_wrap import ObsScript
from app.subapps.khplayer.utils.virtual_cable import patchbay, connect_all, destroy_cable

class ObsVirtualAudioCable(ObsScript):
	description = "Create virtual audio cable in the Pipewire audio server"

	def on_load(self):
		self.app = create_app()
		patchbay.load()
		connect_all(patchbay, self.app.config["PERIPHERALS"])

	def on_unload(self):
		patchbay.load()
		destroy_cable(patchbay)

ObsVirtualAudioCable()
