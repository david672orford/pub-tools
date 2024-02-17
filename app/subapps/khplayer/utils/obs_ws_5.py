# Client for OBS-Websocket 5.x
#
# References:
# * https://github.com/obsproject/obs-websocket
# * https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
#

import json
import websocket
import base64, hashlib
from threading import Thread, current_thread, Lock, Condition
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
		self.subscribers = []
		self.ws = None
		self.next_reqid = 0
		self.next_reqid_lock = Lock()
		self.thread = None
		self.condition = Condition()
		self.responses = {}

		# Connect right away so if browers reconnect they can get events.
		# But supress the error since we have no one to whom to report it.
		# The user will get the error again when he tries to do something
		# which require communication with OBS.
		try:
			self.connect()
		except ObsError as e:
			logger.warning("Failed to connect to OBS: %s", e)

	def subscribe(self, category, func):
		assert category == "scenes"
		self.subscribers.append(func)

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
			# Connect to OBS-Websocket
			ws = websocket.WebSocket()
			ws.connect("ws://%s:%d" % (hostname, port))

			# Read greeting from OBS-Websocket	
			hello = ws.recv()
			logger.debug("hello: %s", hello)
			hello = json.loads(hello)

			if hello["d"]["rpcVersion"] != 1:
				raise ObsError("Incorrect protocol version")

		except ConnectionRefusedError:
			raise ObsError("Not found on {hostname} port {port}".format(**self.config))

		except Exception as e:
			raise ObsError("Cannot connect: " + str(e))

		# Identify (log in) to OBS-Websocket
		req = {
			"op": 1,
			"d": {
				"rpcVersion": 1,
				"eventSubscriptions": 4,
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
			logger.debug("auth response: %s", response)

			if response == "":
				raise ObsError("Incorrect password")

			response = json.loads(response)

			if response["op"] != 2:
				raise ObsError("incorrect opcode")

		except Exception as e:
			raise ObsError("Login failure: " + str(e))

		# We are connected
		self.ws = ws

		# Start receive thread
		self.thread = Thread(target=lambda: self.recv_thread_body(), daemon=True)
		self.thread.start()

	# Close the connection to OBS-Websocket
	def close(self):
		self.ws.close()
		self.ws = None
		self.thread = None
		self.responses = {}

	def recv_thread_body(self):
		logger.debug("Receive thread starting")

		while current_thread() is self.thread:
			try:
				message = self.ws.recv()
			except Exception as e:
				self.close()
				raise ObsError("Receive failure: " + str(e))
			logger.debug("OBS recv message: %s", message)
			if len(message) == 0:
				raise ObsError("Empty response")
			message = json.loads(message)

			if message["op"] == 5:			# Event
				for subscriber in self.subscribers:
					subscriber(message["d"])
			elif message["op"] in (7, 9):
				self.condition.acquire()
				self.responses[message["d"]["requestId"]] = message
				self.condition.notify()
				self.condition.release()
			else:
				logger.warning("Unhandled message:", message)

		logger.debug("Receive thread exiting")

	# Internal: Generate the next request ID
	def get_next_reqid(self):
		self.next_reqid_lock.acquire()
		reqid = self.next_reqid
		self.next_reqid += 1
		self.next_reqid_lock.release()
		return str(reqid)

	# Internal: Send a request
	def ws_write_json(self, message):
		logger.debug("OBS request: %s", message)
		if self.ws is None:
			self.connect()
		try:
			self.ws.send(json.dumps(message))
			self.responses[message["d"]["requestId"]] = None
		except Exception as e:
			self.close()
			raise ObsError("Send failure: " + str(e))

	# Internal: Read response from the websocket to OBS
	def ws_read_json(self, reqid, expected_opcode, req_type=None):
		logger.debug("Waiting for response to %s...", reqid)
		self.condition.acquire()
		while self.responses[reqid] is None:
			#print("responses:", self.responses)
			self.condition.wait()
		response = self.responses.pop(reqid)
		self.condition.release()
		if response["op"] != expected_opcode:
			raise ObsError("incorrect opcode")
		if req_type is not None and response["d"]["requestType"] != req_type:
			raise ObsError("incorrect requestType")
		return response

	# Send a request to OBS and wait for the response
	def request(self, req_type, req_data, raise_on_error=True):
		reqid = self.get_next_reqid()
		self.ws_write_json({
			"op": 6,			# Request
			"d": {
				"requestId": reqid,
				"requestType": req_type,
				"requestData": req_data,
				}
			})
		response = self.ws_read_json(
			reqid,
			expected_opcode=7,	# RequestResponse
			req_type=req_type,
			)
		if raise_on_error and not response["d"]["requestStatus"]["result"]:
			raise ObsError(response)
		return response["d"]	

	# Send a series of requests to OBS
	def request_batch(self, requests, halt_on_failure=False, execution_type=0):
		reqid = self.get_next_reqid()
		self.ws_write_json({
			"op": 8,			# RequestBatch
			"d": {
				"requestId": reqid,
				"haltOnFailure": halt_on_failure,
				"executionType": execution_type,
				"requests": requests,
				}
			})
		response = self.ws_read_json(
			reqid,
			expected_opcode=9,	# RequestBatchResponse
			)
		return response["d"]["results"]

	def create_scene_collection(self, name):
		self.request("CreateSceneCollection", {"sceneCollectionName": name})

	def set_current_scene_collection(self, name):
		self.request("SetCurrentSceneCollection", {"sceneCollectionName": name})

	def get_scene_list(self):
		return self.request("GetSceneList", {})["responseData"]["scenes"]

	def create_scene(self, scene_name, make_unique=False):
		i = 1
		while True:
			try_scene_name = scene_name
			if i > 1:
				try_scene_name += " (%d)" % i
			payload = {
				"sceneName": try_scene_name,
				}
			try:
				self.request("CreateScene", payload)
				return try_scene_name
			except ObsError as e:
				if not make_unique or e.code != 601:		# resource already exists
					raise ObsError(e)
			i += 1

	def remove_scene(self, scene_name):
		self.request("RemoveScene", {"sceneName": scene_name})

	def remove_scenes(self, scene_names):
		requests = []
		for scene_name in scene_names:
			requests.append({
				"requestType": "RemoveScene",
				"requestData": {"sceneName": scene_name},
				})
		self.request_batch(requests)

	def set_current_program_scene(self, scene_name):
		self.request("SetCurrentProgramScene", {"sceneName": scene_name})

	def create_scene_item(self, scene_name, source_name):
		response = self.request("CreateSceneItem", {
			"sceneName": scene_name,
			"sourceName": source_name,
			})
		return response["responseData"]["sceneItemId"]

	def get_scene_item_list(self, scene_name):
		response = self.request("GetSceneItemList", {
			"sceneName": scene_name,
			})
		return response["responseData"]["sceneItems"]

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

