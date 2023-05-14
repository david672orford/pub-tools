import os, sys, types
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.obs_wrap import ObsScript
from app.subapps.khplayer.pipewire import Patchbay
from app.subapps.khplayer.virtual_cable import connect_all, destroy_cable

class ObsVirtualAudioCable(ObsScript):
	description = "Create virtual audio cable in the Pipewire audio server"

	def on_load(self):
		self.app = create_app()
		self.patchbay = Patchbay()
		self.patchbay.load()
		connect_all(self.patchbay, self.app.config["PERIPHERALS"])

	def on_unload(self):
		self.patchbay.load()
		destroy_cable(self.patchbay)

ObsVirtualAudioCable()
