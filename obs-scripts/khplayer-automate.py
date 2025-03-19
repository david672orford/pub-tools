"""
Automate startup and certain aspects of the playing of videos
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))

import re
from subprocess import run
import obspython as obs
from obs_wrap import ObsScript, ObsScriptSourceEventsMixin, ObsWidget

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

		self.yeartext_scene = None				# scene to switch to at OBS start
		self.stopper = MediaStopper(self)		# stops videos before the end
		self.playing_sources = set()			# sources currently playing video
		self.previous_scene = None				# switch to this when playback stops

		# Define this script's configuration GUI
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
			ObsWidget("float", "end_trim", "JW.ORG Videos End Trim", min=0, max=10, step=0.5, default_value=6.0),
			ObsWidget("bool", "debug", "Debug", default_value=False),
			]

	def get_scene_options(self):
		"""Provides the list of scenes for the select box"""
		for scene in self.iter_scenes():
			yield (scene.name, scene.name)

	def on_gui_change(self, settings):
		"""Accept settings from this script's configuration GUI"""
		self.yeartext_scene = settings.yeartext_scene
		self.stopper.end_trim = settings.end_trim
		self.debug = settings.debug
		self.stopper.debug = settings.debug
		if settings.start_vcam:
			# Call from timer to prevent lockups during OBS startup
			def callback():
				obs.obs_frontend_start_virtualcam()
				obs.remove_current_callback()
			obs.timer_add(callback, 1)
		else:
			obs.obs_frontend_stop_virtualcam()
		if settings.screen != "":
			obs.obs_frontend_open_projector("StudioProgram", int(settings.screen), "", "")

	def on_finished_loading(self):
		"""OBS startup complete, scenes are loaded, switch to yeartext scene"""
		if self.debug:
			print("OBS startup complete, switching to yeartext scene")
		self.set_scene(self.yeartext_scene)

	def on_scene_activate(self, scene_name):
		"""Activate a dummy source when Yeartext scene becomes active"""
		if scene_name == self.yeartext_scene:
			self.video_add(DummySource())

	def on_scene_deactivate(self, scene_name):
		"""Deactivate dummy source when Yeartext scene ceases to be active"""
		if scene_name == self.yeartext_scene:
			self.video_remove(DummySource(), return_to_previous=False)
		self.previous_scene = scene_name

	def on_media_started(self, source):
		"""Playing started for any reason"""
		self.video_add(source)

	def on_media_ended(self, source):
		"""Video played to the end without interfernce"""
		self.video_remove(source, return_to_previous=True)

	def on_media_play(self, source):
		"""User pressed the Play button"""
		self.video_add(source)

	def on_media_stopped(self, source):
		"""User pressed the stop button"""
		self.video_remove(source, return_to_previous=True)

	def on_media_pause(self, source):
		"""User pressed the play button"""
		self.video_remove(source, return_to_previous=False)

	def on_source_deactivate(self, source):
		"""Video stopped because user switched away from scene"""
		self.video_remove(source, return_to_previous=False)

	def on_source_destroy(self, source):
		"""Video was removed from scene"""
		if source.id.endswith("_source"):	# i.e., not a scene
			self.video_remove(source, return_to_previous=False)

	def video_add(self, source):
		"""Add a video to the list of those playing"""
		if self.debug:
			print("video_add(%s)" % source.name)
		name = source.name
		if not name in self.playing_sources:
			self.playing_sources.add(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)

			if len(self.playing_sources) == 1:						# went from 0 to 1
				self.act(mute=True, return_to_previous=False)

		# If the video from JW.ORG, set a timer so we can stop it a few seconds
		# from the end just before the copyright and credits card.
		# FIXME: Why does this have to be outside the if?
		if self.is_from_jworg(source):
			self.stopper.set_source(source)

	def video_remove(self, source, return_to_previous=True):
		"""Remove a video from the list of those playing"""
		if self.debug:
			print("video_remove(%s, return_to_previous=%s)" % (source.name, return_to_previous))

		name = source.name
		if name in self.playing_sources:
			self.playing_sources.remove(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)

			if len(self.playing_sources) == 0:			# went from 1 to 0
				self.act(mute=False, return_to_previous=return_to_previous)

		# FIXME: Why does this have to be outside the if?
		self.stopper.cancel(source)

	def is_from_jworg(self, source):
		"""Does the filename of this video suggest it is a video from JW.ORG?"""

		# Find the source filename
		settings = source.settings
		if source.id == "ffmpeg_source":
			filename = settings["local_file"]
		elif source.id == "vlc_source":
			filename = settings["playlist"][0]["value"]
		else:
			filename = ""

		# *_480P.mp4, *_720P.mp4, etc.
		from_jworg = re.search(r"_r\d+P\.mp4$", filename) is not None

		if self.debug:
			print(f"is_from_jworg({source.name}): filename={filename} from_jworg={from_jworg}")

		return from_jworg

	def act(self, mute, return_to_previous):
		"""
		Mute or unmute the default audio source as indicated.
		Optionally return to the home scene as well.
		"""
		if self.debug:
			print("act(mute=%s, return_to_previous=%s)" % (mute, return_to_previous))
		def action():
			if return_to_previous and self.previous_scene is not None:
				self.set_scene(self.previous_scene)
			# TODO: add Windows implementation of muting
			try:
				run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])
			except FileNotFoundError:
				print("pactl not found")
		self.enqueue(action)

class MediaStopper:
	"""Used to set a timer to stop a media source a few minutes before the end"""
	def __init__(self, automate):
		self.debug = False
		self.automate = automate		# pointer to ObsAutomate object
		self.end_trim = None			# will be set by .on_gui_change()
		self.timer_running = False
		self.source = None

		# Called when it is time to stop the media file and return to the home scene
		def _callback():
			if self.debug:
				print("Timer expired, returning to home")
			obs.remove_current_callback()
			self.timer_running = False
			self.source = None
			self.automate.act(mute=False, return_to_previous=True)
			if self.debug:
				print("Timer callback done")
		self.callback = _callback

	def set_source(self, source):
		"""Called when a source (video) which should be stopped early begins playing"""
		if self.debug:
			print(f"set_source({source})")
		if self.end_trim is None:		# If .on_gui_change() not yet called
			return
		assert source.duration > 0
		self._cancel()
		self.source = source
		remaining = (source.duration - source.time)
		remaining -= int(self.end_trim * 1000)
		if self.debug:
			print("Position: %s of %s" % (source.time/1000.0, source.duration/1000.0))
			print("remaining:", remaining/1000.0)
		if remaining > 0:
			obs.timer_add(self.callback, remaining)
			self.timer_running = True

	def cancel(self, source):
		"""Called when the list of playing videos changes"""
		match = self.source is not None and source.uuid == self.source.uuid
		if self.debug:
			print(f"Stopper cancel({source.name}): match={match}")
		if match:
			self._cancel()

	def _cancel(self):
		if self.timer_running:
			if self.debug:
				print(f"Stopping timer for {self.source.name}")
			obs.timer_remove(self.callback)
			self.timer_running = False
		self.source = None

# Used to represent the yeartext so we can mute when it is on screen
class DummySource:
	id = "dummy_source"
	name = "dummy_source"
	uuid = "dummy_source"
	settings = {}

automate = ObsAutomate(debug=True)
