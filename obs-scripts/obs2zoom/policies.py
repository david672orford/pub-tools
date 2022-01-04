# Connect to OBS and monitor its events. Translate some of them
# to remote control actions performed on Zoom

import json
import logging
from obs2zoom.zoom import NoZoomWindow

logger = logging.getLogger(__name__)

class ObsToZoomBase:
	def __init__(self, obs, zoom):
		self.obs = obs
		self.zoom = zoom

	def handle_message(self):
		message = self.obs.recv_message()
		logger.debug("Message: %s", json.dumps(message, indent=2))

		# If this is an event, dispatch it to the appropriate handler (if it exists)
		update_type = message.get('update-type')
		if update_type is not None:
			if update_type == "Exiting":
				return False
			try:
				getattr(self, update_type)(message)
			except AttributeError:
				pass

		return True

class ObsToZoomManual(ObsToZoomBase):

	def VirtualCamStarted(self, event):
		try:
			self.zoom.start_screensharing()
		except NoZoomWindow as e:
			logger.error(str(e))
		except Exception:
			logger.exception("Failed to start screen sharing")

	def VirtualCamStopped(self, event):
		self.zoom.stop_screensharing()

class ObsToZoomAuto(ObsToZoomBase):
	def __init__(self, *args):
		super().__init__(*args)
		self.videos_playing = set()
		self.images_count = 0
		self.vcam_active = self.obs.get_virtualcam_active()
		self.screensharing_active = False

		# Catch up on what we missed.
		# FIXME: assumes any videos found in the current scene are playing
		for source in self.obs.get_current_sources():
			if source['type'] == 'image_source':
				self.images_count += 1
			elif source['type'] == 'ffmpeg_source':
				self.videos_playing.add(source['name'])
		self.update_screensharing()

	#===================================================================
	# Event receivers
	# Keep track of what OBS Studio is doing
	#===================================================================

	def VirtualCamStarted(self, event):
		self.vcam_active = True
		self.update_screensharing()

	def VirtualCamStopped(self, event):
		self.vcam_active = False
		self.update_screensharing()

	def SwitchScenes(self, event):
		self.images_count = 0
		for source in event['sources']:
			if source['type'] == 'image_source':
				self.images_count += 1
		self.update_screensharing()

	def MediaStarted(self, event):
		self.videos_playing.add(event['sourceName'])
		self.update_screensharing()

	def MediaEnded(self, event):
		self.videos_playing.discard(event['sourceName'])
		self.update_screensharing()

	#===================================================================
	# The following functions stop or start screen sharing based on:
	# * Whether videos are playing
	# * Whether still pictures are present in this scene
	# * Whether the virtual camera is enabled
	# * Whether screen sharing is already in the proper state
	#===================================================================

	def update_screensharing(self):
		logger.debug("vcam_active=%s, videos_playing=%s, images_count=%d", self.vcam_active, self.videos_playing, self.images_count)
		if self.vcam_active and (len(self.videos_playing) > 0 or self.images_count > 0):
			self.start_screensharing()
		else:
			self.stop_screensharing()

	def start_screensharing(self):
		if not self.screensharing_active:
			self.pause_all(True)
			try:
				self.zoom.start_screensharing()
			except NoZoomWindow as e:
				logger.error("NoZoomWindow: %s", str(e))
			except Exception:
				logger.exception("Failed to start screen sharing")
			self.pause_all(False)
			self.screensharing_active = True

	def stop_screensharing(self):
		if self.screensharing_active:
			self.zoom.stop_screensharing()
			self.screensharing_active = False

	def pause_all(self, pause):
		for source_name in self.videos_playing:
			request = {"request-type": "PlayPauseMedia", "sourceName": source_name, "playPause": pause}
			logger.debug("Request: %s", json.dumps(request, indent=2))
			self.obs.send_message(request)

