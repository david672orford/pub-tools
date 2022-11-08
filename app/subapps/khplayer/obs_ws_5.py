# Add a scene with a single media item to OBS
# This version communicates with OBS through its Websocket plugin.
#
# We use this library:
# https://pypi.org/project/obsws-python/

import obsws_python as obs
from obsws_python.error import OBSSDKError as OBSError
from urllib.parse import urlparse, unquote
import os
import json
import re
import logging

logger = logging.getLogger(__name__)

class ObsControl:
	def __init__(self, config):
		self.hostname = config['hostname']
		self.port = config['port']
		self.password = config['password']
		self.ws = None

	def connect(self):
		if self.ws is not None:
			return
		self.ws = obs.ReqClient(host=self.hostname, port=self.port, password=self.password)
		print("Version:", self.ws.get_version())

	def add_scene(self, scene_name, media_type, media_file):
		logger.info("Add scene: \"%s\" %s \"%s\"", scene_name, media_type, media_file)
		self.connect()

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
			#payload = {
			#	"sceneName": scene_name,
			#	}
			try:
				#self.ws.send("CreateScene", payload)
				self.ws.create_scene(try_scene_name)
				break
			except OBSError as e:
				if not "already exists" in str(e):
					raise AssertionError(e)
			i += 1

		# Create a source to play our file. Resolve naming conflicts.
		i = 1
		scene_item_id = None
		while True:
			try_source_name = source_name
			if i > 1:
				try_source_name += " (%d)" % i
			payload = {
				'sceneName': scene_name,
				'inputName': try_source_name,
				'inputKind': source_type,
				'inputSettings': source_settings,
				}
			try:
				response = self.ws.send('CreateInput', payload)
				scene_item_id = response.scene_item_id
				break
			except OBSError as e:
				if not "already exists" in str(e):
					raise AssertionError(e)
			i += 1

		# Scale the image to fit the screen
		payload = {
			'sceneName': scene_name,
			'sceneItemId': scene_item_id,
			'sceneItemTransform': {
				'boundsAlignment': 0,
				'boundsWidth': 1280,
				'boundsHeight': 720,
				'boundsType': 'OBS_BOUNDS_SCALE_INNER',
				}
			}
		self.ws.send('SetSceneItemTransform', payload)

		# Enable audio for video files
		if media_type == "video":
			payload = {
				'inputName': source_name,
				'monitorType': "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT",
				}
			self.ws.send('SetInputAudioMonitorType', payload)

