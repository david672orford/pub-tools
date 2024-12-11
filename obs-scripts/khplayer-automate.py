"""
Automate startup and certain aspects of the playing of videos
"""

import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
from obs_wrap import ObsScript, ObsScriptSourceEventsMixin, ObsWidget
from subprocess import run
import obspython as obs

class ObsAutomate(ObsScriptSourceEventsMixin, ObsScript):
	"""
	<style>
		li {
			margin: .2em 0 .2em -1.5em;	/* see https://bugreports.qt.io/browse/QTBUG-1429 */
			}
		ul {
			margin: 0;
			padding: 0;
			}
	</style>
	<h2>KH Player—Automated Actions</h2>
	<ul>
	<li>At OBS Startup:
		<ul>
		<li>Start a fullscreen projector on <b>Projector Screen</b>
		<li>Start the virtual camera
		<li>Switch to the <b>Yeartext Scene</a>
		</ul></li>
	<li>Mute the microphone whenever the <b>Yeartext Scene</b> is displayed.
	<li>Playing Videos:
		<ul>
		<li>Mute microphone at start and unmute afterwards
		<li>Stop the video a few seconds from the end, if it is from JW.ORG
		<li>Return to the previous scene when the video ends
		</ul></li>
	</ul>
	"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.stopper = MediaStopper(self)
		self.yeartext_scene = None
		self.end_trim = None
		self.playing_sources = set()
		self.previous_scene = None

		# Define script configuration GUI
		self.gui = [
			ObsWidget("select", "screen", "Projector Screen", default_value="", options=[
						["", "Not set"],
						["0", "Screen 1"],
						["1", "Screen 2"],
						["2", "Screen 3"],
					]
				),
			ObsWidget("bool", "start_vcam", "Start Virtual Camera", default_value=True),
			ObsWidget("select", "yeartext_scene", "Yeartext Scene", options=self.get_scene_options),
			ObsWidget("float", "end_trim", "JW.ORG Videos End Trim", min=0, max=10, step=0.5, default_value=5.0),
			]

	def get_scene_options(self):
		"""Provides the list of scenes for the select box"""
		for scene in self.iter_scenes():
			yield (scene.name, scene.name)

	def on_gui_change(self, settings):
		"""Accept settings from the script configuration GUI"""
		self.yeartext_scene = settings.yeartext_scene
		self.end_trim = settings.end_trim
		if settings.start_vcam:
			obs.obs_frontend_start_virtualcam()
		else:
			obs.obs_frontend_stop_virtualcam()
		if settings.screen != "":
			obs.obs_frontend_open_projector("StudioProgram", int(settings.screen), "", "")

	def on_finished_loading(self):
		"""OBS startup complete, scenes are loaded, switch to yeartext scene"""
		self.set_scene(self.yeartext_scene)

	def on_scene_activate(self, scene_name):
		"""Only seems to fire if user initiated the switch"""
		if self.debug:
			print("Scene activated:", scene_name)
		if scene_name == self.yeartext_scene:
			self.video_add(DummySource())

	def on_scene_deactivate(self, scene_name):
		if self.debug:
			print("Scene deactivated:", scene_name)
		if scene_name == self.yeartext_scene:
			self.video_remove(DummySource(), return_to_home=False)
		self.previous_scene = scene_name

	def on_media_started(self, source):
		"""Playing started for any reason"""
		self.video_add(source)

	def on_media_ended(self, source):
		"""Video played to the end without interfernce"""
		self.video_remove(source, return_to_home=True)

	def on_media_play(self, source):
		"""User pressed the Play button"""
		self.video_add(source)

	def on_media_stopped(self, source):
		"""User pressed the stop button"""
		self.video_remove(source, return_to_home=True)

	def on_media_pause(self, source):
		"""User pressed the play button"""
		self.video_remove(source, return_to_home=False)

	def on_source_deactivate(self, source):
		"""Video stopped because user switched away from scene"""
		self.video_remove(source, return_to_home=False)

	def on_source_destroy(self, source):
		"""Video was removed from scene"""
		if source.id.endswith("_source"):	# i.e., not a scene
			self.video_remove(source, return_to_home=False)

	def video_add(self, source):
		"""Add a video to the list of those playing"""
		if self.debug:
			print("video_add(%s)" % source)
		name = source.name
		if not name in self.playing_sources:
			self.playing_sources.add(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)

			if len(self.playing_sources) == 1:						# went from 0 to 1
				self.enqueue(lambda: self.act(mute=True, return_to_home=False))

		# If the video from JW.ORG, set a timer so we can stop it a few seconds
		# from the end just before the copyright and credits card.
		if self.is_from_jworg(source):
			self.stopper.set_source(source)

	def video_remove(self, source, return_to_home=True):
		"""Remove a video from the list of those playing"""
		if self.debug:
			print("video_remove(%s, return_to_home=%s)" % (source, return_to_home))

		name = source.name
		if name in self.playing_sources:
			self.playing_sources.remove(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)

			if len(self.playing_sources) == 0:			# went from 1 to 0
				self.enqueue(lambda: self.act(mute=False, return_to_home=return_to_home))

		self.stopper.cancel(source)

	def is_from_jworg(self, source):
		"""Does the filename of this video suggest it is from JW.ORG?"""
		# Find the source filename
		settings = source.settings
		print("Source settings:", settings)
		if source.id == "ffmpeg_source":
			filename = settings["local_file"]
		elif source.id == "vlc_source":
			filename = settings["playlist"][0]["value"]
		else:
			filename = ""

		# *_480P.mp4
		return re.search(r"_r\d+P\.mp4$", filename) is not None

	def act(self, mute, return_to_home):
		"""
		Mute or unmute the default audio source as indicated.
		Optionally return to the home scene as well.
		"""
		if self.debug:
			print("act(mute=%s, return_to_home=%s)" % (mute, return_to_home))
		if return_to_home:
			if self.previous_scene is not None:
				self.set_scene(self.previous_scene)
			else:
				self.set_scene(self.yeartext_scene)
		run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])

# Used to set a timer to stop a media source a few minutes before the end
class MediaStopper:
	def __init__(self, automate):
		self.automate = automate
		self.timer_running = False
		self.source = None

		# Called when it is time to stop the media file and return to the home scene
		def _callback():
			if self.automate.debug:
				print("Timer expired, returning to home")
			obs.remove_current_callback()
			self.timer_running = False
			self.source = None
			self.automate.act(mute=False, return_to_home=True)
			if self.automate.debug:
				print("Timer callback done")
		self.callback = _callback

	def set_source(self, source):
		"""Called when a source (video) which should be stopped early begins playing"""
		if self.automate.debug:
			print("Set source:", source.name, source.duration)
		assert source.duration > 0
		self.source = source
		remaining = (source.duration - source.time)
		remaining -= int(self.automate.end_trim * 1000)
		if self.automate.debug:
			print("Position: %s of %s" % (source.time/1000.0, source.duration/1000.0))
			print("remaining:", remaining/1000.0)
			print("stop after:", remaining/1000.0)
		if remaining > 0:
			obs.timer_add(self.callback, remaining)
			self.timer_running = True

	def cancel(self, source):
		"""Called when the list of playing videos changes"""
		if self.automate.debug:
			print("Stopper cancel()")
		if source is not self.source:
			print("Different source")
			return
		if self.timer_running:
			print("Stopping timer")
			obs.timer_remove(self.callback)
			self.timer_running = False
		self.source = None

# Used to represent the yeartext so we can mute when it is on screen
class DummySource:
	id = "dummy_source"
	name = "dummy_source"
	settings = {}

ObsAutomate(debug=False)
