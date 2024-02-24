# Client for OBS-Websocket 5.x
#
# References:
# * https://github.com/obsproject/obs-websocket
# * https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
#

import websocket, json, base64, hashlib
from threading import Thread, current_thread, Lock, Condition
import queue
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

class ObsResponsePending:
	pass

class ObsControlBase:
	def __init__(self, config):
		self.config = config
		self.subscribers = []
		self.ws = None
		self.next_reqid = 0
		self.next_reqid_lock = Lock()
		self.recv_thread = None
		self.responses_lock = Condition()
		self.responses = {}
		self.event_queue = queue.SimpleQueue()

		# Connect right away so if browers reconnect after a server restart, they will
		# receive events right away. But if we cannot connect to OBS, suppress the error
		# since we have no one to whom to report it.
		# The user will get the error again when he tries to do something
		# which require communication with OBS.
		try:
			self.connect()
		except ObsError as e:
			logger.warning("Failed to connect to OBS: %s", e)

	# Register an event callback function. Currently only scenes-event
	# subscriptions are implemented.
	def subscribe(self, category, func):
		assert category == "scenes"
		self.subscribers.append(func)

	# Open the websocket connection to OBS, log in, and start a receive thread.
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
			try:
				hello = json.loads(hello)
			except json.JSONDecodeError:
				raise ObsError("Server Hello is not valid JSON")

			if hello["d"]["rpcVersion"] != 1:
				raise ObsError("Incorrect protocol version in server Hello")

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

			try:
				response = json.loads(response)
			except json.JSONDecodeError:
				raise ObsError("Identify response is not valid JSON")

			if response["op"] != 2:
				raise ObsError("incorrect opcode")

		except Exception as e:
			raise ObsError("Login failure: " + str(e))

		# We are connected
		self.ws = ws

		# Start receive thread
		self.recv_thread = Thread(target=lambda: self._recv_thread_body(), daemon=True)
		self.recv_thread.start()

	# Close the connection to OBS-Websocket
	def close(self):
		self.ws.close()
		self.ws = None
		self.recv_thread = None
		self.responses = {}

	# Internal: receive messages from OBS-Websocket and dispatch them as events
	# or insert them into self.responses[].
	def _recv_thread_body(self):
		logger.debug("Receive thread starting")

		# Read messages from OBS until .close() is called
		while current_thread() is self.recv_thread:
			self._recv_message()

			while True:
				try:
					event = self.event_queue.get_nowait()
				except queue.Empty:
					break
				for subscriber in self.subscribers:
					subscriber(event)

		# Give None responses to all outstanding requests
		self.responses_lock.acquire()
		for reqid in self.responses.keys():
			self.responses[reqid] = None
		self.responses_lock.notify()
		self.responses_lock.release()

		logger.debug("Receive thread exiting!")

	# Internal: read the next message from OBS-Websocket and place it in the proper queue
	def _recv_message(self):
		try:
			message = self.ws.recv()
		except Exception as e:
			self.close()
			raise ObsError("Receive failure: " + str(e))

		logger.debug("OBS recv message: %s", message)
		if len(message) == 0:
			raise ObsError("Empty response from OBS. Disconnected?")
		try:
			message = json.loads(message)
		except json.JSONDecodeError:
			raise ObsError("Response is not valid JSON")

		if message["op"] == 5:			# Event
			self.event_queue.put(message["d"])
		elif message["op"] in (7, 9):
			self.responses_lock.acquire()
			self.responses[message["d"]["requestId"]] = message
			self.responses_lock.notify()
			self.responses_lock.release()
		else:
			logger.warning("Unhandled message: %s", message)

	# Internal: Send a request to OBS-Websocket
	def _ws_write_json(self, message):
		logger.debug("OBS request: %s", message)
		if self.ws is None:
			self.connect()
		self.responses[message["d"]["requestId"]] = ObsResponsePending
		try:
			self.ws.send(json.dumps(message))
		except Exception as e:
			self.close()
			raise ObsError("Send failure: " + str(e))

	# Internal: Read response from OBS-Websocket
	def _ws_read_json(self, reqid, expected_opcode, req_type=None):
		logger.debug("Waiting for response to %s...", reqid)

		# Event handlers are run from the receive thread. They may in turn make
		# requests to OBS-Websocket. In such as case, we need to keep receiving
		# and queueing messages from OBS-Websocket until we get our own when
		# we can return, the event handler can finish, and the regular receive
		# loop resumes its work.
		if current_thread() is self.recv_thread:
			while self.responses[reqid] is ObsResponsePending:
				self._recv_message()

		# Wait for response with proper reqid to appear in self.responses[]
		self.responses_lock.acquire()
		self.responses_lock.wait_for(lambda: self.responses[reqid] is not ObsResponsePending, timeout=10)
		response = self.responses.pop(reqid)
		self.responses_lock.release()

		if response is ObsResponsePending:
			raise ObsError("response timeout waiting for %s" % reqid)
		if type(response) is not dict:
			raise ObsError("response is not dict: %s" % response)
		if response["op"] != expected_opcode:
			raise ObsError("incorrect opcode")
		if req_type is not None and response["d"]["requestType"] != req_type:
			raise ObsError("incorrect requestType")
		return response

	# Internal: Generate the next request ID
	def _get_next_reqid(self):
		self.next_reqid_lock.acquire()
		reqid = self.next_reqid
		self.next_reqid += 1
		self.next_reqid_lock.release()
		return str(reqid)

	# Send a request to OBS and wait for the response
	def request(self, req_type, req_data, raise_on_error=True):
		reqid = self._get_next_reqid()
		self._ws_write_json({
			"op": 6,			# Request
			"d": {
				"requestId": reqid,
				"requestType": req_type,
				"requestData": req_data,
				}
			})
		response = self._ws_read_json(
			reqid,
			expected_opcode=7,	# RequestResponse
			req_type=req_type,
			)
		if raise_on_error and not response["d"]["requestStatus"]["result"]:
			raise ObsError(response)
		return response["d"]	

	# Send a series of requests to OBS
	def request_batch(self, requests, halt_on_failure=False, execution_type=0):
		reqid = self._get_next_reqid()
		self._ws_write_json({
			"op": 8,			# RequestBatch
			"d": {
				"requestId": reqid,
				"haltOnFailure": halt_on_failure,
				"executionType": execution_type,
				"requests": requests,
				}
			})
		response = self._ws_read_json(
			reqid,
			expected_opcode=9,	# RequestBatchResponse
			)
		return response["d"]["results"]

	def create_scene_collection(self, name):
		self.request("CreateSceneCollection", {"sceneCollectionName": name})

	def set_current_scene_collection(self, name):
		self.request("SetCurrentSceneCollection", {"sceneCollectionName": name})

	def get_scene_list(self):
		result = self.request("GetSceneList", {})["responseData"]
		result["scenes"] = list(reversed(result["scenes"]))			# OBS-Websocket returns a backwards list
		return result

	def get_scene_uuid(self, scene_name):
		for scene in self.get_scene_list()["scenes"]:
			if scene["sceneName"] == scene_name:
				return scene["sceneUuid"]
		return None

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
				response = self.request("CreateScene", payload)
				return {
					"sceneName": try_scene_name,
					"sceneUuid": response["responseData"]["sceneUuid"],
					}
		
			except ObsError as e:
				if not make_unique or e.code != 601:		# resource already exists
					raise ObsError(e)
			i += 1

	def remove_scene(self, scene_uuid):
		self.request("RemoveScene", {"sceneUuid": scene_uuid})

	def remove_scenes(self, scene_uuids):
		requests = []
		for scene_uuid in scene_uuids:
			requests.append({
				"requestType": "RemoveScene",
				"requestData": {"sceneUuid": scene_uuid},
				})
		self.request_batch(requests)

	def get_current_program_scene(self):
		response = self.request("GetCurrentProgramScene", {})
		return response["responseData"]

	def set_current_program_scene(self, scene_uuid):
		self.request("SetCurrentProgramScene", {"sceneUuid": scene_uuid})

	def create_scene_item(self, scene_uuid, source_name=None, source_uuid=None):
		req = {
			"sceneUuid": scene_uuid,
			}
		if source_name is not None:
			req["sourceName"] = source_name
		if source_uuid is not None:
			req["sourceUuid"] = source_uuid
		response = self.request("CreateSceneItem", req)
		return response["responseData"]["sceneItemId"]

	def get_scene_item_list(self, uuid):
		response = self.request("GetSceneItemList", {
			"sceneUuid": uuid,
			})
		return response["responseData"]["sceneItems"]

	def get_scene_item_transform(self, scene_uuid, scene_item_id):
		response = self.request("GetSceneItemTransform", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			})
		return response["responseData"]["sceneItemTransform"]

	def set_scene_item_transform(self, scene_uuid, scene_item_id, transform):
		response = self.request("SetSceneItemTransform", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			"sceneItemTransform": transform,
			})

	def create_input(self, scene_uuid, input_name, input_kind, input_settings={}):
		response = self.request("CreateInput", {
			"sceneUuid": scene_uuid,
			"inputName": input_name,
			"inputKind": input_kind,
			"inputSettings": input_settings,
			})
		return response["responseData"]["sceneItemId"]

	def get_input_settings(self, input_uuid):
		response = self.request("GetInputSettings", {
			"inputUuid": input_uuid,
			})
		return response["responseData"]

	def set_input_settings(self, input_uuid, input_settings={}, overlay=True):
		self.request("SetInputSettings", {
			"inputUuid": input_uuid,
			"inputSettings": input_settings,
			"overlay": overlay,
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

	def get_source_screenshot(self, source_uuid):
		response = self.request("GetSourceScreenshot", {
			"sourceUuid": source_uuid,
			"imageFormat": "jpeg",
			"imageWidth": 96,
			"imageHeight": 54,
			})
		data = response["responseData"]["imageData"]
		assert data.startswith("data:")
		return data

