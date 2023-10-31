# OBS Studio Plugin which automatically starts the virtual camera and
# fullscreen projector when the program starts

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
from obs_wrap import ObsScript, ObsWidget
from subprocess import run
import obspython as obs

class ObsStartup(ObsScript):
	description = """
		<style>
			li {
				margin: .2em 0 .2em -1.5em;	/* see https://bugreports.qt.io/browse/QTBUG-1429 */
				}
		</style>
		<h2>KH Player—Startup</h2>
		<p>When OBS is launched:</p>
		<ul>
		<li>Switch to the indicated scene
		<li>Start the virtual camera
		<li>Start a fullscreen projector on indicated screen
		</ul>
		"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.scene = None
		self.prev_scene = None

		# Define script configuration GUI
		self.gui = [
			ObsWidget("select", "scene", "Initial Scene", options=self.get_scene_options),
			ObsWidget("select", "screen", "Projector Screen", default_value="2", options=[
						["0", "Screen 1"],
						["1", "Screen 2"],
						["2", "Screen 3"],
					]
				)
			]

	# Provides the list of scenes for the select box
	def get_scene_options(self):
		for scene in self.iter_scenes():
			yield (scene.name, scene.name)

	# Accept settings from the script configuration GUI
	def on_gui_change(self, settings):
		obs.obs_frontend_start_virtualcam()
		obs.obs_frontend_open_projector("StudioProgram", int(settings.screen), "", "")
		self.scene = settings.scene

	def on_finished_loading(self):
		self.set_mute(True)
		self.set_scene(self.scene)
		self.cur_scene = self.scene

	# Only seems to fire if user initiated the switch
	def on_scene_change(self, scene_name):
		print("Scene:", scene_name)
		if scene_name == self.scene:
			self.enqueue(lambda: self.set_mute(True))
		elif self.prev_scene == self.scene:
			self.enqueue(lambda: self.set_mute(False))
		self.prev_scene = scene_name

	def set_mute(self, mute):
		print("Mute:", mute)
		run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])

	def on_unload(self):
		obs.obs_frontend_stop_virtualcam()

ObsStartup(debug=True)
