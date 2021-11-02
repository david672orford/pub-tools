# Connect to OBS over websocket and manipulate its scene list

from urllib.parse import urlparse, unquote
from obswebsocket import obsws, requests, events, exceptions
from obswebsocket.base_classes import Baserequests, Baseevents
import os
import json
import re
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class ObsControl:
	def __init__(self):
		self.virtual_cam_started = False
		self.obs = obsws("localhost", 4444, "secret")
		self.obs.register(self.on_VirtualCamStarted, VirtualCamStarted)
		self.obs.register(self.on_VirtualCamStopped, VirtualCamStopped)

	def connect(self):
		try:
			self.obs.connect()
		except exceptions.ConnectionFailure:
			return False

		version = self.obs.call(requests.GetVersion())
		logger.info("OBS Studio version: %s" % version.getObsStudioVersion())
		logger.info("OBS-Websocket version: %s" % version.getObsWebsocketVersion())

		vcam = self.obs.call(GetVirtualCamStatus())
		self.virtual_cam_started = vcam.isVirtualCam()
		logger.info("Virtual cam started: %s" % self.virtual_cam_started)

		self.start_virtual_camera()

		return True

	def disconnect(self):
		self.obs.disconnect()

	def on_VirtualCamStarted(self, event):
		logger.info("Virtual cam started")
		self.virtual_cam_started = True

	def on_VirtualCamStopped(self, event):
		logger.info("Virtual cam stopped")
		self.virtual_cam_started = False

	# If the virtual camera is not running, start it.
	def start_virtual_camera(self):
		if not self.virtual_cam_started:
			result = self.obs.call(StartVirtualCam())
			assert result.status, result

	# Dump the lists of scenes and their sources. We use this to better
	# understand how to add scenes and sources.
	def list_scenes(self):
		for scene in self.obs.call(requests.GetSceneList()).getScenes():
			print("==================================================================")
			print("scene:", json.dumps(scene, indent=2, ensure_ascii=False))
			for source in scene['sources']:
				item_properties = self.obs.call(requests.GetSceneItemProperties(source, scene_name=scene['name']))
				print("scene item:", json.dumps(item_properties.datain, indent=2, ensure_ascii=False))
				source_settings = self.obs.call(requests.GetSourceSettings(sourceName=source['name'], sourceType=source['type'])).getSourceSettings()
				print("source settings:", json.dumps(item_properties.datain, indent=2, ensure_ascii=False))

	def add_scene(self, scene_name, media_type, media_file):
		logger.info("Add scene: \"%s\" %s \"%s\"", scene_name, media_type, media_file)

		# Get basename of media file
		if re.match(r"^https?://", media_file, re.I):
			path = urlparse(media_file).path
			if path.endswith("/"):
				source_name = path.split("/")[-2]
			else:
				source_name = path.split("/")[-1]
			source_name = unquote(source_name)
		else:
			source_name = os.path.basename(media_file)

		# Select the appropriate OBS suurce type and build its settings
		if media_type == "video":
			source_type = "ffmpeg_source"
			source_settings = {'local_file': media_file}
		elif media_type == "image":
			source_type = "image_source"
			source_settings = {'file': media_file}
		elif media_type == "web":
			source_type = "browser_source"
			source_settings = {'url': media_file, 'width': 1280, 'height': 720, 'css': ''}
		else:
			raise AssertionError("Unsupported media_type: %s" % media_type)

		logger.info(" Source: %s \"%s\"", source_type, source_name)
		logger.info(" Source settings: %s", source_settings)

		# Add a new scene. Resolve naming conflicts.
		i = 1
		while True:
			try_scene_name = scene_name
			if i > 1:
				try_scene_name += " (%d)" % i
			result = self.obs.call(requests.CreateScene(try_scene_name))
			if result.status:
				scene_name = try_scene_name
				break
			if not "already exists" in result.datain['error']:
				raise AssertionError(result)
			i += 1

		# Create a source to play our file. Resolve naming conflicts.
		i = 1
		while True:
			try_source_name = source_name
			if i > 1:
				try_source_name += " (%d)" % i
			result = self.obs.call(requests.CreateSource(
				try_source_name,
				source_type,
				scene_name,
				source_settings,
				))
			if result.status:
				source_name = try_source_name
				break
			if not "already exists" in result.datain['error']:
				raise AssertionError(result)
			i += 1

		# Scale the image to fit the screen
		result = self.obs.call(requests.SetSceneItemProperties(
			item = source_name,
			scene_name = scene_name,
			bounds = dict(
				alignment = 0,
				x = 1280,
				y = 720,
				type = 'OBS_BOUNDS_SCALE_INNER'
				)
			))
		assert result.status, result

		# Enable audio for video files
		if media_type == "video":
			result = self.obs.call(requests.SetAudioMonitorType(
				sourceName = source_name,
				monitorType = "monitorAndOutput"
				))
			assert result.status, result

#=============================================================================
# Not yet implemented in obs-websocket-py
#=============================================================================

class VirtualCamStarted(Baseevents):
	def __init__(self):
		super().__init__()
		self.name = 'VirtualCamStarted'
events.VirtualCamStarted = VirtualCamStarted

class VirtualCamStopped(Baseevents):
	def __init__(self):
		super().__init__()
		self.name = 'VirtualCamStopped'
events.VirtualCamStopped = VirtualCamStopped

class GetVirtualCamStatus(Baserequests):
	def __init__(self):
		super().__init__()
		self.name = 'GetVirtualCamStatus'
		self.datain['isVirtualCam'] = None
	def isVirtualCam(self):
		return self.datain['isVirtualCam']

class StartVirtualCam(Baserequests):
	def __init__(self):
		super().__init__()
		self.name = 'StartVirtualCam'

