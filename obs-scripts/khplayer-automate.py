import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".libs"))
from obs_wrap import ObsScript, ObsScriptSourceEventsMixin, ObsWidget
from subprocess import run
import obspython as obs

class MediaStopper:
	def __init__(self, automate):
		self.automate = automate
		self.timer_running = False
		def _callback():
			print("Timer expired!")
			obs.remove_current_callback()
			self.timer_running = False
			self.automate.act(mute=False, return_to_home=True)
			print("Timer callback done")
		self.callback = _callback

	def set(self, milliseconds):
		obs.timer_add(self.callback, milliseconds)
		self.timer_running = True

	def cancel(self):
		if self.timer_running:
			obs.timer_remove(self.callback)
			self.timer_running = False

class DummySource:
	id = "dummy_source"
	name = "dummy_source"
	settings = {}

class ObsAutomate(ObsScriptSourceEventsMixin, ObsScript):
	description = """
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
    	    <li>Return to <b>Stage Scene</b> when the video ends
			</ul></li>
		</ul>
		"""

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.stopper = MediaStopper(self)
		self.yeartext_scene = None
		self.stage_scene = None
		self.end_trim = None
		self.playing_sources = set()
		self.output = None

		# Define script configuration GUI
		self.gui = [
			ObsWidget("select", "screen", "Projector Screen", default_value="2", options=[
						["0", "Screen 1"],
						["1", "Screen 2"],
						["2", "Screen 3"],
					]
				),
			ObsWidget("select", "yeartext_scene", "Yeartext Scene", options=self.get_scene_options),
			ObsWidget("select", "stage_scene", "Stage Scene", options=self.get_scene_options),
			ObsWidget("float", "end_trim", "JW.ORG Videos End Trim", min=0, max=10, step=0.5, default_value=5.0),
			ObsWidget("button", "output", "Start Output", callback=self.on_start_output),
			]

	# Provides the list of scenes for the select box
	def get_scene_options(self):
		for scene in self.iter_scenes():
			yield (scene.name, scene.name)

	# Accept settings from the script configuration GUI
	def on_gui_change(self, settings):
		self.yeartext_scene = settings.yeartext_scene
		self.stage_scene = settings.stage_scene
		self.end_trim = settings.end_trim
		obs.obs_frontend_open_projector("StudioProgram", int(settings.screen), "", "")

	def on_finished_loading(self):
		self.set_scene(self.yeartext_scene)
		obs.obs_frontend_start_virtualcam()

	def on_start_output(self):
		print("Start output")
		if self.output is None:
			self.output = obs.obs_output_create("pulse_output", "pulse_output", None, None)
		print("Output:", self.output)
		print("Start:", obs.obs_output_start(self.output))
		print("Start output: done")

	def on_unload(self):
		if self.output is not None:
			obs.obs_output_stop(output)
			obs.obs_output_destroy(output)
			self.output = None

	# Only seems to fire if user initiated the switch
	def on_scene_activate(self, scene_name):
		if self.debug:
			print("Scene:", scene_name)
		if scene_name == self.yeartext_scene:
			self.video_add(DummySource())

	def on_scene_deactivate(self, scene_name):
		if self.debug:
			print("Scene deactivated:", scene_name)
		if scene_name == self.yeartext_scene:
			self.video_remove(DummySource(), return_to_home=False)

	# Playing started for any reason
	def on_media_started(self, source):
		self.video_add(source)

	# Video played to the end without interfernce
	def on_media_ended(self, source):
		self.video_remove(source, return_to_home=True)

	# User pressed the Play button
	def on_media_play(self, source):
		self.video_add(source)

	# User pressed the stop button
	def on_media_stopped(self, source):
		self.video_remove(source, return_to_home=True)

	# User pressed the play button
	def on_media_pause(self, source):
		self.video_remove(source, return_to_home=False)

	# Video stopped because user switched away from scene
	def on_source_deactivate(self, source):
		self.video_remove(source, return_to_home=False)

	# Video was removed from scene
	def on_source_destroy(self, source):
		if source.id.endswith("_source"):	# i.e., not a scene
			self.video_remove(source, return_to_home=False)

	# Add a video to the list of those playing
	def video_add(self, source):
		if self.debug:
			print("video_add(%s)" % source)
		name = source.name
		if not name in self.playing_sources:
			self.playing_sources.add(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)

			if len(self.playing_sources) == 1:						# went from 0 to 1
				self.enqueue(lambda: self.act(mute=True, return_to_home=False))

		# Find the source filename
		settings = source.settings
		print("Source settings:", settings)
		if source.id == "ffmpeg_source":
			filename = settings["local_file"]
		elif source.id == "vlc_source":
			filename = settings["playlist"][0]["value"]
		else:
			filename = ""

		# If the filename looks like that of a video from JW.ORG, set a timer
		# so we can stop it a few seconds from the end just before the
		# copyright and credits card.
		self.stopper.cancel()
		if re.search(r"_r\d+P\.mp4$", filename):	# *_480P.mp4
			print("Position: %s of %s" % (source.time/1000.0, source.duration/1000.0))
			remaining = (source.duration - source.time)
			print("remaining:", remaining/1000.0)
			remaining -= int(self.end_trim * 1000)
			print("stop after:", remaining/1000.0)
			if remaining > 0:
				self.stopper.set(remaining)

	# Remove a video from the list of those playing
	def video_remove(self, source, return_to_home=True):
		if self.debug:
			print("video_remove(%s, return_to_home=%s)" % (source, return_to_home))
		name = source.name
		if name in self.playing_sources:
			self.playing_sources.remove(name)
			if self.debug:
				print("playing_sources:", self.playing_sources)

			if len(self.playing_sources) == 0:			# went from 1 to 0
				self.enqueue(lambda: self.act(mute=False, return_to_home=return_to_home))

			self.stopper.cancel()

	# Mute or unmute the default audio source as indicated.
	# Optionally return to the home scene as well.
	def act(self, mute, return_to_home):
		if self.debug:
			print("act(mute=%s, return_to_home=%s)" % (mute, return_to_home))
		if return_to_home:
			self.set_scene(self.stage_scene)
		run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])

ObsAutomate(debug=False)

