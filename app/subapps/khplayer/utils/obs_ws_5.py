# Client for OBS-Websocket 5.x
#
# References:
# * https://github.com/obsproject/obs-websocket
# * https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md
#

import os.path
import websocket, json, base64, hashlib
from threading import Thread, current_thread, Lock, Condition
from time import sleep
import queue
import logging

logger = logging.getLogger(__name__)

class ObsError(Exception):
	def __init__(self, message:str, *, response:dict=None):
		super().__init__(message)
		if response is not None:
			self.code = response["d"]["requestStatus"]["code"]
			self.comment = response["d"]["requestStatus"].get("comment")
		else:
			self.code = 0
			self.comment = response
	def __str__(self):
		if self.code == 0:
			return super().__str__()
		else:
			return "<ObsError %s code=%d comment=%s>" % (super().__str__(), self.code, repr(self.comment))

class ObsHangup(ObsError):
	pass

class ObsResponsePending:
	pass

class ObsControlBase:
	def __init__(self, config):
		self.config = config
		self.event_intents = {
			"Config": 2,
			"Scenes": 4,
			"SceneItems": 128,
			"Ui": 1024,
			}
		self.subscribers = {
			2: [],
			4: [],
			128: [],
			1024: [],
			}
		self.ws = None
		self.next_reqid = 0
		self.next_reqid_lock = Lock()
		self.recv_thread = None
		self.responses_lock = Condition()
		self.responses = {}
		self.event_queue = queue.SimpleQueue()

		# FIXME: We have disabled this because it attempted to connect to OBS even
		# in cases where KH Player was not going to be used such as when running
		# flask CLI commands to manage the publications DB.
		#
		# Connect right away so if browers reconnect after a server restart, they will
		# receive events right away. But if we cannot connect to OBS, suppress the error
		# since we have no one to whom to report it. The user will get the error again
		# when he tries to do something which require communication with OBS.
		#try:
		#	self.connect()
		#except ObsError as e:
		#	logger.warning("Failed to connect to OBS: %s", e)

	# Register an event callback function. Currently only scenes-event
	# subscriptions are implemented.
	def subscribe(self, category, func):
		assert category in self.event_intents
		self.subscribers[self.event_intents[category]].append(func)

	# Open the websocket connection to OBS, log in, and start a receive thread.
	def connect(self):
		if self.config is None:
			raise ObsError("Connection not configured")

		try:
			hostname = self.config["hostname"]
			port = self.config["port"]
			password = self.config["password"]
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
			if not self.config.get("obs_websocket_enabled", True):
				raise ObsError("The OBS-Websocket plugin is not enabled")
			raise ObsError("Not found on {hostname} port {port}".format(**self.config))

		except Exception as e:
			raise ObsError("Cannot connect: " + str(e))

		# Identify (log in) to OBS-Websocket
		req = {
			"op": 1,
			"d": {
				"rpcVersion": 1,
				# FIXME
				#"eventSubscriptions": 2 | 4 | 128 | 1024,
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

		# Tell the receive thread to stop
		self.recv_thread = None

		# Give None responses to all outstanding requests
		self.responses_lock.acquire()
		for reqid in self.responses.keys():
			self.responses[reqid] = None
		self.responses_lock.notify()
		self.responses_lock.release()

	# Internal: receive messages from OBS-Websocket and dispatch them as events
	# or insert them into self.responses[].
	def _recv_thread_body(self):
		logger.debug("Receive thread starting")

		# Read messages from OBS until .close() is called or OBS hangs up
		while current_thread() is self.recv_thread:
			try:
				self._recv_one_message()
			except ObsHangup:
				break

			# Dispatch events to subscribers
			while True:
				try:
					event = self.event_queue.get_nowait()
				except queue.Empty:
					break
				logger.debug("Event: %s", event)
				for subscriber in self.subscribers.get(event["eventIntent"], []):
					subscriber(event)

		logger.debug("Receive thread exiting!")

	# Internal: read the next message from OBS-Websocket and place it in the proper queue
	def _recv_one_message(self):
		try:
			message = self.ws.recv()
		except Exception as e:
			self.close()
			raise ObsError("Receive failure: " + str(e))
		logger.debug("OBS recv message: %s", message)

		if len(message) == 0:
			self.close()
			raise ObsHangup("Zero-length read")

		try:
			message = json.loads(message)
		except json.JSONDecodeError:
			raise ObsError("Response is not valid JSON")
		assert type(message) is dict

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
		# loop resumes its work. No need to lock since only we will be making
		# this mesage appear in self.responses[].
		if current_thread() is self.recv_thread:
			while self.responses[reqid] is ObsResponsePending:
				self._recv_one_message()

		# Wait for response with proper reqid to appear in self.responses[]
		self.responses_lock.acquire()
		self.responses_lock.wait_for(lambda: self.responses[reqid] is not ObsResponsePending, timeout=10)
		response = self.responses.pop(reqid)
		self.responses_lock.release()

		if response is None:
			raise ObsHangup("OBS terminated connection")
		if response is ObsResponsePending:
			raise ObsError("response timeout waiting for %s" % reqid)
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
			expected_opcode = 7,	# RequestResponse
			req_type = req_type,
			)
		if raise_on_error and not response["d"]["requestStatus"]["result"]:
			raise ObsError("Request failed", response=response)
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

	#=========================================================================
	# Implementation Information
	#=========================================================================

	def get_version(self):
		return self.request("GetVersion", {})

	#=========================================================================
	# Profiles
	#=========================================================================

	def create_profile(self, name, reuse=False):
		try:
			self.request("CreateProfile", {"profileName": name})
		except ObsError as e:
			if e.code == 601 and reuse:		# ResourceAlreadyExists
				self.set_current_profile(name)
			else:
				raise

	def set_current_profile(self, name):
		self.request("SetCurrentProfile", {"profileName": name})

	#=========================================================================
	# Scene Collections
	#=========================================================================

	def create_scene_collection(self, name, reuse=False):
		try:
			self.request("CreateSceneCollection", {"sceneCollectionName": name})
		except ObsError as e:
			if e.code == 601 and reuse:		# ResourceAlreadyExists
				self.set_current_scene_collection(name)
			else:
				raise

	def set_current_scene_collection(self, name):
		self.request("SetCurrentSceneCollection", {"sceneCollectionName": name})

	#=========================================================================
	# Scenes
	#=========================================================================

	def get_scene_list(self):
		while True:
			try:
				result = self.request("GetSceneList", {})["responseData"]
				# OBS-Websocket returns a backwards list
				result["scenes"] = list(reversed(result["scenes"]))
				return result
			except ObsError as e:
				if e.code != 207:		# 207 OBS Not ready
					raise
			sleep(.1)

	def get_group_list(self):
		result = self.request("GetGroupList", {})
		return result["responseData"]["groups"]

	def get_current_preview_scene(self):
		response = self.request("GetCurrentPreviewScene", {})
		return response["responseData"]

	def set_current_preview_scene(self, scene_uuid):
		self.request("SetCurrentPreviewScene", {"sceneUuid": scene_uuid})

	def get_current_program_scene(self):
		response = self.request("GetCurrentProgramScene", {})
		return response["responseData"]

	def set_current_program_scene(self, scene_uuid):
		self.request("SetCurrentProgramScene", {"sceneUuid": scene_uuid})

	def get_scene_uuid(self, scene_name):
		for scene in self.get_scene_list()["scenes"]:
			if scene["sceneName"] == scene_name:
				return scene["sceneUuid"]
		return None

	def create_scene(self, scene_name:str, *, make_unique:bool=False):
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
				if not make_unique or e.code != 601:		# 601 is resource already exists
					raise
			i += 1

	def set_scene_name(self, scene_uuid, scene_name):
		self.request("SetSceneName", {
			"sceneUuid": scene_uuid,
			"newSceneName": scene_name,
			})

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

	#=========================================================================
	# Scene items
	#=========================================================================

	def get_scene_item_id(self, scene_uuid, source_name):
		try:
			response = self.request("GetSceneItemId", {
				"sceneUuid": scene_uuid,
				"sourceName": source_name,
				})
			return response["responseData"]["sceneItemId"]
		except ObsError as e:
			if e.code == 600:
				return None
			else:
				raise

	def get_scene_item_list(self, scene_uuid):
		response = self.request("GetSceneItemList", {
			"sceneUuid": scene_uuid,
			})
		return response["responseData"]["sceneItems"]

	def create_scene_item(self, *, scene_uuid:str, source_uuid:str=None, source_name:str=None):
		assert source_uuid is not None or source_name is not None
		req = {
			"sceneUuid": scene_uuid,
			}
		if source_uuid is not None:
			req["sourceUuid"] = source_uuid
		elif source_name is not None:
			req["sourceName"] = source_name
		response = self.request("CreateSceneItem", req)
		return response["responseData"]["sceneItemId"]

	def remove_scene_item(self, scene_uuid, scene_item_id):
		self.request("RemoveSceneItem", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			})

	def get_scene_item_transform(self, scene_uuid, scene_item_id):
		response = self.request("GetSceneItemTransform", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			})
		return response["responseData"]["sceneItemTransform"]

	def set_scene_item_transform(self, scene_uuid:str, scene_item_id:int, transform:dict):
		response = self.request("SetSceneItemTransform", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			"sceneItemTransform": transform,
			})

	def get_scene_item_private_settings(self, scene_uuid, scene_item_id):
		response = self.request("GetSceneItemPrivateSettings", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			})
		return response["responseData"]["sceneItemSettings"]

	def set_scene_item_private_settings(self, scene_uuid:str, scene_item_id:int, settings:dict):
		response = self.request("SetSceneItemPrivateSettings", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			"sceneItemSettings": settings,
			})

	def set_scene_item_index(self, scene_uuid:str, scene_item_id:int, index:int):
		response = self.request("SetSceneItemIndex", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			"sceneItemIndex": index,
			})

	def set_scene_item_enabled(self, scene_uuid:str, scene_item_id:int, enabled:bool):
		response = self.request("SetSceneItemEnabled", {
			"sceneUuid": scene_uuid,
			"sceneItemId": scene_item_id,
			"sceneItemEnabled": enabled,
			})

	#=========================================================================
	# Inputs (a kind of source)
	#=========================================================================

	def get_input_list(self):
		return self.request("GetInputList", {})["responseData"]["inputs"]

	def get_input_uuid(self, input_name:str):
		for item in self.get_input_list():
			if item["inputName"] == input_name:
				return item["inputUuid"]
		return None

	def create_input(self, *, scene_uuid:str, input_name:str, input_kind:str, input_settings:dict={}):
		response = self.request("CreateInput", {
			"sceneUuid": scene_uuid,
			"inputName": input_name,
			"inputKind": input_kind,
			"inputSettings": input_settings,
			})
		result = response["responseData"]
		result["inputName"] = input_name
		return result

	def get_input_settings(self, name:str=None, uuid:str=None):
		params = {}
		if name is not None:
			params["inputName"] = name
		else:
			params["inputUuid"] = uuid
		response = self.request("GetInputSettings", params)
		return response["responseData"]["inputSettings"]

	def set_input_settings(self, name:str=None, uuid:str=None, settings:dict={}, overlay:bool=True):
		params = {
			"inputSettings": settings,
			"overlay": overlay,
			}
		if name is not None:
			params["inputName"] = name
		else:
			params["inputUuid"] = uuid
		self.request("SetInputSettings", params)

	#=========================================================================
	# Virtual Camera
	#=========================================================================

	def get_virtual_camera_status(self):
		return self.request("GetVirtualCamStatus", {})["responseData"]["outputActive"]

	def set_virtual_camera_status(self, status):
		if status is None:
			self.request("ToggleVirtualCam", {})
		elif status:
			self.request("StartVirtualCam", {})
		else:
			self.request("StopVirtualCam", {})

	#=========================================================================
	# Output
	#=========================================================================

	def get_video_settings(self):
		return self.request("GetVideoSettings", {})["responseData"]

	def set_video_settings(self, settings):
		self.request("SetVideoSettings", settings)

	def get_monitor_list(self):
		return self.request("GetMonitorList", {})["responseData"]["monitors"]

	def start_output_projector(self, monitor):
		self.request("OpenVideoMixProjector", {
			"videoMixType": "OBS_WEBSOCKET_VIDEO_MIX_TYPE_PROGRAM",
			"monitorIndex": monitor,
			})

	#=========================================================================
	# Screenshots
	#=========================================================================

	def get_source_screenshot(self, source_uuid:str, width=96, height=54):
		"""Return a thumbnail-sized screenshot of the indicated sources as a data URL"""
		response = self.request("GetSourceScreenshot", {
			"sourceUuid": source_uuid,
			"imageFormat": "jpeg",
			"imageWidth": width,
			"imageHeight": height,
			"imageCompressionQuality": 85,
			})
		data = response["responseData"]["imageData"]
		assert data.startswith("data:")
		return data

	def save_source_screenshot(self, source_uuid:str, filename, image_format="jpeg"):
		self.request("SaveSourceScreenshot", {
			"sourceUuid": source_uuid,
			"imageFormat": image_format,
			"imageFilePath": os.path.abspath(filename),
			})
