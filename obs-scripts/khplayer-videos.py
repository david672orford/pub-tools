import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
from obs_wrap import ObsScript, ObsScriptSourceEventsMixin, ObsWidget
from subprocess import run
import obspython as obs

class MediaStopper:
	def __init__(self):
		self.source = None
		def _callback():
			print("In timer callback")
			obs.remove_current_callback()
			self.source.stop()
			self.source = None
			print("Timer callback done")
		self.callback = _callback

	def set(self, source, milliseconds):
		assert self.source is None
		self.source = source
		obs.timer_add(self.callback, milliseconds)

	def cancel(self):
		if self.source is not None:
			obs.timer_remove(self.callback)
			self.source = None

class ObsAutoMute(ObsScriptSourceEventsMixin, ObsScript):
	description = """
		<style>
			li {
				margin: .2em 0 .2em -1.5em;	/* see https://bugreports.qt.io/browse/QTBUG-1429 */
				}
		</style>
		<h2>KH Player—Video Actions</h2>
		<ul>
	    <li>Mute microphone while videos play
	    <li>Stop videos from JW.ORG a few seconds before the end
	    <li>Switch to scene selected below when any video ends
		</ul>
		"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# Define script configuration GUI
		self.gui = [
			ObsWidget("select", "home_scene", "Home Scene", options=self.get_scene_options),
			ObsWidget("float", "stop", "Seconds from End", min=0, max=10, step=0.5, default_value=5.0),
			]

		# Video sources currently playing
		self.playing_sources = set()

		# Scene to which to return when video ends
		self.home_scene = None

		#
		self.stopper = MediaStopper()
		self.stop = None

	# Provides the list of scenes for the select box
	def get_scene_options(self):
		for scene in self.iter_scenes():
			yield (scene.name, scene.name)

	# Accept settings from the script configuration GUI
	def on_gui_change(self, settings):
		self.home_scene = settings.home_scene
		self.stop = settings.stop
		print("changed:", self.home_scene, self.stop)

	def on_media_started(self, source):
		self.video_add(source)

	def on_media_pause(self, source):
		self.video_remove(source, return_to_home=False)

	def on_media_ended(self, source):
		self.video_remove(source, return_to_home=True)

	def on_source_destroy(self, source):
		self.video_remove(source, return_to_home=False)

	def on_source_deactivate(self, source):
		self.video_remove(source, return_to_home=False)

	# Add a video to the list of those playing
	def video_add(self, source):
		name = source.name
		if not name in self.playing_sources:
			self.playing_sources.add(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)
			if len(self.playing_sources) == 1:						# went from 0 to 1
				self.enqueue(lambda: self.act(True, False))

			self.stopper.cancel()
			settings = source.settings
			print("Settings:", settings)
			if source.id == "ffmpeg_source":
				filename = settings["local_file"]
			elif source.id == "vlc_source":
				filename = settings["playlist"][0]["value"]
			else:
				filename = ""
			if re.search(r"_r\d+P\.mp4$", filename):		# jw.org video, example: *_r480P.mp4
				print("Position: %s of %s" % (source.time/1000.0, source.duration/1000.0))
				remaining = (source.duration - source.time)
				print("remaining:", remaining/1000.0)
				remaining -= int(self.stop * 1000)
				print("stop after:", remaining/1000.0)
				if remaining > 0:
					self.stopper.set(source, remaining)

	# Remove a video from the list of those playing
	def video_remove(self, source, return_to_home=True):
		name = source.name
		if name in self.playing_sources:
			self.playing_sources.remove(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)
			if len(self.playing_sources) == 0:						# went from 1 to 0
				self.enqueue(lambda: self.act(False, return_to_home))
				# FIXME: we are assuming the last remaining video is the same as the first
				if self.debug:
					print("Canceling timer")
				self.stopper.cancel()

	# Mute or unmute the default audio source as indicated.
	# Optionally return to the home scene as well.
	def act(self, mute, return_to_home):
		if self.debug:
			print("act(mute=%s, return_to_home=%s)" % (mute, return_to_home))
		if return_to_home:
			self.set_scene(self.home_scene)
		run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])

ObsAutoMute(debug=True)

