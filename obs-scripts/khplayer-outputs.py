# OBS Studio Plugin which automatically starts the virtual camera and
# fullscreen projector when the program starts

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
from obs_wrap import ObsScript, ObsWidget
import obspython as obs

class ObsAutostartOutputs(ObsScript):
	description = "Autostart the virtual camera and fullscreen projector on the selected monitor."

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Define script configuration GUI
		self.settings_widgets = [
			ObsWidget("select", "screen", "Screen", default_value="2", options=[
						["0", "Screen 1"],
						["1", "Screen 2"],
						["2", "Screen 3"],
					]
				)
			]

	# Accept settings from the script configuration GUI
	def on_settings(self, settings):
		obs.obs_frontend_start_virtualcam()
		obs.obs_frontend_open_projector("StudioProgram", int(settings.screen), "", "")

	def on_unload(self):
		obs.obs_frontend_stop_virtualcam()

ObsAutostartOutputs()
