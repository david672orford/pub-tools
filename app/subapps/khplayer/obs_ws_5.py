# Add a scene with a single media item to OBS
# This version communicates with OBS through the OBS-Websocket plugin version 5.x.
#
# References:
# * https://github.com/obsproject/obs-websocket
# * https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
#

import os, re, json
import websocket
import base64, hashlib
from urllib.parse import urlparse, unquote
from glob import glob
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
		if self.code == 0:
			return self.comment
		else:
			return "<ObsError code=%d comment=%s>" % (self.code, repr(self.comment))

class ObsControlBase:
	def __init__(self, config):
		self.config = config
		self.ws = None
		self.reqid = 0

	def connect(self):
		if self.config is None:
			raise ObsError("Connection not configured")

		try:
			hostname = self.config['hostname']
			port = self.config['port']
			password = self.config['password']
		except KeyError:
			raise ObsError("Bad connection configuration")

		try:
			ws = websocket.WebSocket()
			ws.connect("ws://%s:%d" % (hostname, port))
	
			hello = ws.recv()
			print("hello:", hello)
			hello = json.loads(hello)

			if hello["d"]["rpcVersion"] != 1:
				raise ObsError("Incorrect protocol version")

		except ConnectionRefusedError:
			raise ObsError("Not found on {hostname} port {port}".format(**self.config))

		except Exception as e:
			raise ObsError("Cannot connect: " + str(e))
	
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
								(password + hello["d"]["authentication"]["salt"]).encode()
								).digest()
							).decode()
						+ hello["d"]["authentication"]["challenge"]
						).encode()
					).digest()
				).decode()

		try:	
			ws.send(json.dumps(req))
			response = ws.recv()
			print("auth response:", response)

			if response == "":
				raise ObsError("Incorrect password")

			response = json.loads(response)

			if response["op"] != 2:
				raise ObsError("incorrect opcode")

		except Exception as e:
			raise ObsError("Login failure: " + str(e))

		# We are connected
		self.ws = ws

	# Send a request to OBS and wait for the response
	def request(self, req_type, req_data, raise_on_error=True):
		if self.ws is None:
			self.connect()

		self.reqid += 1

		try:
			self.ws.send(json.dumps({
				"op": 6,		# request
				"d": {
					"requestId": str(self.reqid),
					"requestType": req_type,
					"requestData": req_data,
					}
				}))

			response = self.ws.recv()
			logger.debug("OBS response: %s", response)
			if len(response) == 0:
				raise ObsError("Empty response")

			response = json.loads(response)

			if response["op"] != 7:
				raise ObsError("incorrect opcode")
			if response["d"]["requestType"] != req_type:
				raise ObsError("incorrect requestType")
			if response["d"]["requestId"] != str(self.reqid):
				raise ObsError("incorrect requestId")

		except Exception as e:
			self.ws.close()
			self.ws = None
			raise ObsError(str(e))

		if raise_on_error and not response["d"]["requestStatus"]["result"]:
			raise ObsError(response)
		return response["d"]	

	def create_scene_collection(self, name):
		self.request("CreateSceneCollection", {"sceneCollectionName": name})

	def get_scene_list(self):
		return self.request("GetSceneList", {})["responseData"]["scenes"]

	def create_scene(self, scene_name):
		self.request("CreateScene", { "sceneName": scene_name })

	def remove_scene(self, scene_name):
		self.request("RemoveScene", {"sceneName": scene_name})

	def set_current_program_scene(self, scene_name):
		self.request("SetCurrentProgramScene", {"sceneName": scene_name})

	def create_scene_item(self, scene_name, source_name):
		response = self.request("CreateSceneItem", {
			"sceneName": scene_name,
			"sourceName": source_name,
			})
		return response["responseData"]["sceneItemId"]

	def create_input(self, scene_name, input_name, input_kind, input_settings={}):
		response = self.request("CreateInput", {
			"sceneName": scene_name,
			"inputName": input_name,
			"inputKind": input_kind,
			"inputSettings": input_settings,
			})
		return response["responseData"]["sceneItemId"]

	def set_input_settings(self, input_name, input_settings={}):
		self.request("SetInputSettings", {
			"inputName": input_name,
			"inputSettings": input_settings,
			"overlay": True,
			})

	def scale_input(self, scene_name, scene_item_id, scene_item_transform={}):
		xform = {
				'boundsAlignment': 0,
				'boundsWidth': 1280,
				'boundsHeight': 720,
				'boundsType': 'OBS_BOUNDS_SCALE_INNER',
				}
		xform.update(scene_item_transform)
		self.request('SetSceneItemTransform', 
			{
			'sceneName': scene_name,
			'sceneItemId': scene_item_id,
			'sceneItemTransform': xform,
 			})

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

# Add higher-level methods to do specific things we need
class ObsControl(ObsControlBase):
	camera_scene_name = "Camera"
	camera_input_name = "Camera Input"
	camera_input_settings = {
		"buffering": False,
		"input": 0,
		#"pixelformat": 1196444237,		# Motion-JPEG
		"pixelformat": 875967048,		# H.264
		"resolution": 83886800,			# 1280x720
		}

	zoom_scene_name = "Zoom"
	zoom_input_name = "Zoom Capture"

	split_scene_name = "Split Screen"

	# Create a scene for a video or image file.
	# Center it and scale to reach the edges.
	# For videos enable audio monitoring.
	def add_media_scene(self, scene_name, media_type, media_file):
		logger.info("Add media_scene: \"%s\" %s \"%s\"", scene_name, media_type, media_file)

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

		# Create a source (now called an input) to play our file. Resolve naming conflicts.
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

		## Scale the image to fit the screen
		#payload = {
		#	'sceneName': scene_name,
		#	'sceneItemId': scene_item_id,
		#	'sceneItemTransform': {
		#		'boundsAlignment': 0,
		#		'boundsWidth': 1280,
		#		'boundsHeight': 720,
		#		'boundsType': 'OBS_BOUNDS_SCALE_INNER',
		#		}
		#	}
		#self.request('SetSceneItemTransform', payload)
		self.scale_input(scene_name, scene_item_id)

		# Enable audio for video files
		if media_type == "video":
			payload = {
				'inputName': source_name,
				'monitorType': "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT",
				}
			self.request('SetInputAudioMonitorType', payload)

	def create_input_with_reuse(self, scene_name, input_name, input_kind, input_settings):
		try:
			scene_item_id = self.create_input(
				scene_name = scene_name,
				input_name = input_name,
				input_kind = input_kind,
				input_settings = input_settings
				)
		except ObsError as e:
			if e.code != 601:
				raise(ObsError(e))
			scene_item_id = self.create_scene_item(
				scene_name = scene_name,
				source_name = input_name,
				)
		return scene_item_id

	def list_cameras(self):
		for dev in glob("/sys/class/video4linux/*"):
			with open(os.path.join(dev, "name")) as fh:
				name = fh.read().strip()
			with open(os.path.join(dev, "index")) as fh:
				index = int(fh.read().strip())
			if index == 0:
				yield ("/dev/" + os.path.basename(dev), name)

	def camera_dev_lookup(self, camera_name):
		for dev_node, display_name in self.list_cameras():
			if display_name == camera_name:
				return dev_node
		return None

	def reconnect_camera(self, camera_name):
		self.camera_input_settings["device_id"] = self.camera_dev_lookup(camera_name)
		self.set_input_settings(self.camera_input_name, self.camera_input_settings)

	def add_camera_input(self, scene_name, camera_dev_name):
		self.camera_input_settings["device_id"] = self.camera_dev_lookup(camera_dev_name)
		scene_item_id = self.create_input_with_reuse(
			scene_name = scene_name,
			input_name = self.camera_input_name,
			input_kind = "v4l2_input",
			input_settings = self.camera_input_settings,
			)
		return scene_item_id

	def add_zoom_input(self, scene_name):
		scene_item_id = self.create_input(
			scene_name = scene_name,
			input_name = "Zoom Capture",
			input_kind = "xcomposite_input",
			input_settings = {
				"capture_window": "Zoom Conference",
				"show_cursor": False,
				}
			)
		return scene_item_id

	def create_camera_scene(self, camera_dev_name):
		self.create_scene(self.camera_scene_name)
		scene_item_id = self.add_camera_input(self.camera_scene_name, camera_dev_name)
		#self.scale_input(self.camera_scene_name, scene_item_id)

	def create_zoom_scene(self):
		self.create_scene(self.zoom_scene_name)
		scene_item_id = self.add_zoom_input(self.zoom_scene_name)
		self.scale_input(self.zoom_scene_name, scene_item_id)

	def create_split_scene(self, camera_dev_name):
		self.create_scene(self.split_scene_name)
		scene_item_id = self.add_camera_input(self.split_scene_name, camera_dev_name)
		self.scale_input(self.split_scene_name, scene_item_id, {
			"positionX": 0.0,
			"positionY": 180.0,
			"scaleX": 0.5,
			"scaleY": 0.5,
			"height": 360.0,
			"width": 640.0,
			})
		scene_item_id = self.add_zoom_input(self.split_scene_name)
		self.scale_input(self.split_scene_name, scene_item_id, {
			"positionX": 640.0,
			"positionY": 180.0,
			"scaleX": 0.5,
			"scaleY": 0.5,
			"height": 360.0,
			"width": 640.0,
			})

