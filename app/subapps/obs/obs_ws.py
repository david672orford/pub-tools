# Add a scene with a single media item to OBS
# This version uses OBS-Websocket

import websocket
from urllib.parse import urlparse, unquote
import os
import json
import re
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

class ObsControl:
	def __init__(self, hostname="localhost", port=4444, password="secret"):
		self.hostname = hostname
		self.port = port
		self.password = password
		self.ws = None
		self.id = 1

	def connect(self):
		if self.ws is not None:
			return

		ws = websocket.WebSocket()
		ws.connect("ws://%s:%d" % (self.hostname, self.port))
		self.ws = ws		# we are connected

		response = self.request({"request-type": "GetAuthRequired"})
		assert response['status'] == 'ok'

		if response.get('authRequired'):
			secret = base64.b64encode(hashlib.sha256((self.password + response['salt']).encode('utf-8')).digest())
			auth = base64.b64encode(hashlib.sha256(secret + response['challenge'].encode('utf-8')).digest()).decode('utf-8')
			response = self.request({"request-type": "Authenticate", "auth": auth})
			assert response['status'] == 'ok'

	def request(self, data, wait=True):
		data["message-id"] = str(self.id)
		self.id += 1
		logger.debug("request: %s", json.dumps(data, indent=2, ensure_ascii=False))
		self.ws.send(json.dumps(data))
		if not wait:
			return None
		while True:
			response = json.loads(self.ws.recv())
			logger.debug("response: %s", json.dumps(response, indent=2, ensure_ascii=False))
			if response.get('message-id') == data['message-id']:
				break
		return response

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
			response = self.request({'request-type': 'CreateScene', 'sceneName': try_scene_name})
			if response['status'] == 'ok':
				scene_name = try_scene_name
				break
			if not "already exists" in response['error']:
				raise AssertionError(response)
			i += 1

		# Create a source to play our file. Resolve naming conflicts.
		i = 1
		while True:
			try_source_name = source_name
			if i > 1:
				try_source_name += " (%d)" % i
			response = self.request({
				'request-type': 'CreateSource',
				'sourceName': try_source_name,
				'sourceKind': source_type,
				'sceneName': scene_name,
				'sourceSettings': source_settings,
				})
			if response['status'] == 'ok':
				source_name = try_source_name
				break
			if not "already exists" in response['error']:
				raise AssertionError(response)
			i += 1

		# Scale the image to fit the screen
		response = self.request({
			'request-type': 'SetSceneItemProperties',
			'item': source_name,
			'scene-name': scene_name,
			'bounds': {
				'alignment': 0,
				'x': 1280,
				'y': 720,
				'type': 'OBS_BOUNDS_SCALE_INNER',
				}
			})
		assert response['status'] == 'ok', response

		# Enable audio for video files
		if media_type == "video":
			response = self.request({
				'request-type': 'SetAudioMonitorType',
				'sourceName': source_name,
				'monitorType': "monitorAndOutput",
				})
			assert response['status'] == 'ok', result

