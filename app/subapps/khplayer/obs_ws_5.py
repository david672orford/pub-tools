# Add a scene with a single media item to OBS
# This version communicates with OBS through the OBS-Websocket plugin version 5.x.
#
# References:
# * https://github.com/obsproject/obs-websocket
# * https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
#

import websocket
import base64
import hashlib
from urllib.parse import urlparse, unquote
import os
import json
import re
import logging

logger = logging.getLogger(__name__)

class ObsError(Exception):
	def __init__(self, response):
		super().__init__()
		if type(response) is dict:
			self.code = response["d"]["requestStatus"]["code"]
			self.comment = response["d"]["requestStatus"].get("comment")
		elif type(response) is ObsError:
			self.code = response.code
			self.comment = response.comment
		else:
			self.code = 0
			self.comment = response
	def __str__(self):
		return "<ObsError code=%d comment=%s" % (self.code, repr(self.comment))

class ObsControl:
	def __init__(self, config):
		self.hostname = config['hostname']
		self.port = config['port']
		self.password = config['password']
		self.ws = None
		self.reqid = 0

	def connect(self):
		self.ws = websocket.WebSocket()
		self.ws.connect("ws://%s:%d" % (self.hostname, self.port))

		hello = json.loads(self.ws.recv())
		print("hello:", hello)
		assert hello["d"]["rpcVersion"] == 1

		req = {
			"op": 1,
			"d": {
				"rpcVersion": 1,
				"eventSubscriptions": 0,
				}
			}

		if "authentication" in hello["d"]:			# if server requires authentication,
			req["d"]["authentication"] = base64.b64encode(
				hashlib.sha256(
						(
						base64.b64encode(
							hashlib.sha256(
								(self.password + hello["d"]["authentication"]["salt"]).encode()
								).digest()
							).decode()
						+ hello["d"]["authentication"]["challenge"]
						).encode()
					).digest()
				).decode()

		self.ws.send(json.dumps(req))
		response = json.loads(self.ws.recv())
		print("auth response:", response)
		assert response["op"] == 2

	def request(self, req_type, req_data, raise_on_error=True):
		self.reqid += 1

		self.ws.send(json.dumps({
			"op": 6,		# request
			"d": {
				"requestId": str(self.reqid),
				"requestType": req_type,
				"requestData": req_data,
				}
			}))

		try:
			response = json.loads(self.ws.recv())
			print("OBS response:", response)
			assert response["op"] == 7, "incorrect opcode"
			assert response["d"]["requestType"] == req_type, "incorrect requestType"
			assert response["d"]["requestId"] == str(self.reqid), "incorrect requestId"
		except json.JSONDecodeError:
			raise ObsError("Unparsable response")
		except AssertionError as e:
			raise ObsError("Assertion failed: %s" % e)

		if raise_on_error and not response["d"]["requestStatus"]["result"]:
			raise ObsError(response)
		return response["d"]	

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
			payload = {
				"sceneName": try_scene_name,
				}
			try:
				result = self.request("CreateScene", payload)
				scene_name = try_scene_name
				break
			except ObsError as e:
				if e.code != 601:		# resource already exists
					raise ObsError(e)
			i += 1

		# Create a source (no called input) to play our file. Resolve naming conflicts.
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
				response = self.request('CreateInput', payload)
				source_name = try_source_name
				scene_item_id = response["responseData"]["sceneItemId"]
				break
			except ObsError as e:
				if e.code != 601:		# resource already exists
					raise ObsError(e)
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
		self.request('SetSceneItemTransform', payload)

		# Enable audio for video files
		if media_type == "video":
			payload = {
				'inputName': source_name,
				'monitorType': "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT",
				}
			self.request('SetInputAudioMonitorType', payload)

	def create_scene_collection(self, name):
		self.request("CreateSceneCollection", {"sceneCollectionName": name})

	def get_scene_list(self):
		return self.request("GetSceneList", {})["responseData"]["scenes"]

	def remove_scene(self, scene_name):
		self.request("RemoveScene", {"sceneName": scene_name})

	def set_current_program_scene(self, scene_name):
		self.request("SetCurrentProgramScene", {"sceneName": scene_name})

	def get_virtual_camera_status(self):
		return self.request("GetVirtualCamStatus", {})["responseData"]["outputActive"]

	def set_virtual_camera_status(self, status):
		if status is None:
			self.request("ToggleVirtualCam", {})
		elif status:
			self.request("StartVirtualCam", {})
		else:
			self.request("StopVirtualCam", {})

	def get_monitor_list(self):
		return self.request("GetMonitorList", {})["responseData"]["monitors"]

	def start_output_projector(self, monitor):
		self.request("OpenVideoMixProjector", {
			"videoMixType": "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM",
			"monitorIndex": monitor,
			})

