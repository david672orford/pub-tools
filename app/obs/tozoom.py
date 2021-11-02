# Connect to OBS and monitor its events. Translate some of them
# to remote control actions performed on Zoom

from obswebsocket import obsws, events
from obswebsocket.exceptions import ConnectionFailure
from time import sleep
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ObsToZoom:
	def __init__(self, obs, zoom):
		self.obs = obs
		self.zoom = zoom
		self.playing = set()
		self.images = 0
		self.sharing = False
		self.obs.register(self)

	# Event dispatcher
	def __call__(self, event):
		logger.debug("OBS Event: %s" % event.name)
		try:
			getattr(self, event.name)(event)
		except AttributeError:
			pass
		except Exception as e:
			logger.warning("Exception: %s" % e)

	def SwitchScenes(self, event):
		logger.debug("  Scene name: %s" % event.getSceneName())
		logger.debug("  Sources: %s" % event.getSources())
		self.images = 0
		for source in event.getSources():
			if source['type'] == 'image_source':
				self.images += 1
		self.update_screensharing()

	def MediaStarted(self, event):
		logger.debug("  Started source: %s" % event.getSourceName())
		self.playing.add(event.getSourceName())
		self.update_screensharing()

	def MediaPaused(self, event):
		logger.debug("  Paused source: %s" % event.getSourceName())
		self.zoom.stop_screensharing()
		self.zoom.open_sharing_dialog(hide=True)
	
	def MediaPlaying(self, event):
		logger.debug("  Playing source: %s" % event.getSourceName())
		self.zoom.start_screensharing()

	def MediaEnded(self, event):
		logger.debug("  Ended source: %s" % event.getSourceName())
		self.playing.discard(event.getSourceName())
		self.update_screensharing()

	def update_screensharing(self):
		logger.debug("************************")
		should_share = len(self.playing) > 0 or self.images > 0
		logger.debug("should share: %s" % should_share)
		if should_share:
			if not self.sharing:
				logger.debug("Must start screen sharing")
				# does not return?
				#self.obs.start_virtual_camera()
				self.zoom.start_screensharing()
				logger.debug("sharing started")
		elif self.sharing:
			logger.debug("Must stop screen sharing")
			self.zoom.stop_screensharing()
		self.sharing = should_share

