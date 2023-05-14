import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.obs_wrap import ObsScript, ObsScriptSourceEventsMixin
from subprocess import run

class ObsAutoMute(ObsScriptSourceEventsMixin, ObsScript):
	playing_sources = set()
	description = "Automatically mute microphone when a video is playing. Unmute and return to first scene when it stops."

	def on_source_destroy(self, source):
		self.playing_sources.discard(source.name)
		if len(self.playing_sources) == 0:
			self.enqueue(self.video_end)

	def on_media_started(self, source):
		self.playing_sources.add(source.name)
		#print("playing_sources:", self.playing_sources)
		if len(self.playing_sources) == 1:
			self.enqueue(self.video_start)

	def on_media_ended(self, source):
		self.playing_sources.discard(source.name)
		#print("playing_sources:", self.playing_sources)
		if len(self.playing_sources) == 0:
			self.enqueue(self.video_end)

	def on_media_pause(self, source):
		self.playing_sources.discard(source.name)
		#print("playing_sources:", self.playing_sources)
		if len(self.playing_sources) == 0:
			print("Just unmute")
			self.enqueue(lambda: self.set_mute(False))

	def video_start(self):
		#print("video start")
		self.set_mute(True)

	def video_end(self):
		#print("video end")
		self.set_mute(False)
		self.set_scene("* Stage")

	def set_mute(self, mute):
		run(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "1" if mute else "0"])

ObsAutoMute()
