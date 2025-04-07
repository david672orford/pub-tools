import os, re
from time import sleep
from urllib.parse import urlparse, unquote, urlencode
import logging

logger = logging.getLogger(__name__)

from .obs_ws_5 import ObsControlBase, ObsError
from ....utils.config import get_config, put_config

class ObsControl(ObsControlBase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.app = None

		# Scene list hooks. We have to install the event handler
		# immediately, since it needs to come before the one
		# in view_scenes.py so we can pass "before" to it.
		self._scene_list = None
		self._scene_pos = {}
		self.subscribe("Config", lambda event: self.event(event))
		self.subscribe("Scenes", lambda event: self.event(event))
		self.subscribe("Ui", lambda event: self.event(event))

	def init_app(self, app):
		self.app = app

	#============================================================================
	# OBS-Websocker provides no way to reorder scene or control the position
	# of new scenes. For this reason we maintain or own scene order and
	# wrap .get_scene_list().
	#============================================================================

	def get_scene_list(self):
		return self.scene_list

	def get_studio_mode_enabled(self):
		return self.scene_list["currentPreviewSceneUuid"] is not None

	def get_current_preview_scene(self):
		return {
			"sceneName": self.scene_list["currentPreviewSceneName"],
			"sceneUuid": self.scene_list["currentPreviewSceneUuid"],
			}

	def get_current_program_scene(self):
		return {
			"sceneName": self.scene_list["currentProgramSceneName"],
			"sceneUuid": self.scene_list["currentProgramSceneUuid"],
			}

	@property
	def scene_list(self):
		if self._scene_list is None:

			# Initial load scene list is from OBS
			self._scene_list = super().get_scene_list()

			# Restore our saved scene order.
			scenes = []
			for scene_uuid in get_config("SCENE_ORDER", []):
				try:
					scenes.append(self.scene_list["scenes"].pop(self.get_scene_index(scene_uuid)))
				except KeyError:
					pass

			# New scenes go at the end.
			for scene in self.scene_list["scenes"]:
				scenes.append(scene)

			self.scene_list["scenes"] = scenes

		return self._scene_list

	def event(self, event):
		if self._scene_list is None:
			return
		data = event["eventData"]
		if data.get("isGroup", False):
			return
		match event["eventType"]:
			case "CurrentSceneCollectionChanged":
				self._scene_list = None
				self._scene_pos = {}
			case "CurrentProgramSceneChanged":
				self.scene_list["currentProgramSceneUuid"] = data["sceneUuid"]
				self.scene_list["currentProgramSceneName"] = data["sceneName"]
			case "CurrentPreviewSceneChanged":
				self.scene_list["currentPreviewSceneUuid"] = data["sceneUuid"]
				self.scene_list["currentPreviewSceneName"] = data["sceneName"]
			case "StudioModeStateChanged":
				scenes = self.scene_list
				if data["studioModeEnabled"]:
					scenes["currentPreviewSceneUuid"] = scenes["currentProgramSceneUuid"]
					scenes["currentPreviewSceneName"] = scenes["currentProgramSceneName"]
				else:
					scenes["currentPreviewSceneUuid"] = None
					scenes["currentPreviewSceneName"] = None
			case "SceneCreated":
				scene_name = re.sub(r" \(\d+\)$", "", data["sceneName"])
				pos = self._scene_pos.pop(scene_name, None)
				if pos is not None and pos < len(self.scene_list["scenes"]):
					data["before"] = self.scene_list["scenes"][pos]["sceneUuid"]	# for handler in view_scenes.py
					self.scene_list["scenes"].insert(pos, data)
				else:
					self.scene_list["scenes"].append(data)
				with self.app.app_context():
					self._save_scene_order()
			case "SceneRemoved":
				self.scene_list["scenes"].pop(self.get_scene_index(data["sceneUuid"]))
				with self.app.app_context():
					self._save_scene_order()
			case "SceneNameChanged":
				self.scene_list["scenes"][self.get_scene_index(data["sceneUuid"])]["sceneName"] = data["sceneName"]

	def create_scene(self, scene_name:str, *, make_unique:bool=False, pos:int=None):
		if pos is not None:
			self._scene_pos[scene_name] = pos
		return super().create_scene(scene_name, make_unique=make_unique)

	# Return the index of the first scene with a name which does
	# not begin with any of the characters in skiplist.
	def select_scene_pos(self, skiplist:str=None):
		if skiplist is None:
			return None
		pos = 0
		for scene in self.scene_list["scenes"]:
			scene_name = scene["sceneName"]
			if len(scene_name) == 0:		# shouldn't happen, but...
				break
			if scene_name[0] not in skiplist:
				break
			pos += 1
		return pos

	def get_scene_index(self, uuid):
		scenes = self.get_scene_list()["scenes"]
		for i in range(len(scenes)):
			if scenes[i]["sceneUuid"] == uuid:
				return i
		raise KeyError()

	def get_scene_name(self, uuid):
		scenes = self.get_scene_list()["scenes"]
		for i in range(len(scenes)):
			if scenes[i]["sceneUuid"] == uuid:
				return scenes[i]["sceneName"]
		raise KeyError()

	# Change the position of a scene in the scene list
	def move_scene(self, uuid, new_index):
		i = self.get_scene_index(uuid)
		scene = self.scene_list["scenes"].pop(i)
		self.scene_list["scenes"].insert(new_index, scene)
		self._save_scene_order()

	def _save_scene_order(self):
		uuids = []
		for scene in self.get_scene_list()["scenes"]:
			uuids.append(scene["sceneUuid"])
		put_config("SCENE_ORDER", uuids)

	#============================================================================
	# Create a scene for a video or image file.
	# Center it and scale to reach the edges.
	# For videos enable audio monitoring.
	#============================================================================

	def add_media_scene(self, scene_name:str, media_type:str, media_file:str, *, thumbnail:str=None, subtitle_track:str=None, skiplist:str=None):
		logger.info("Add media_scene: \"%s\" %s \"%s\"", scene_name, media_type, media_file)

		# Get basename of media file
		if re.match(r"^https?://", media_file, re.I):
			parsed_url = urlparse(media_file)
			path = parsed_url.path
			if path == "":
				input_name = parsed_url.hostname
			elif path.endswith("/"):
				input_name = path.split("/")[-2]
			else:
				input_name = path.split("/")[-1]
			input_name = unquote(input_name)
		else:
			input_name = os.path.basename(media_file)

		# Select the appropriate OBS source type and build its settings
		if media_type == "audio":
			input_kind = "ffmpeg_source"
			input_setting = {
				"local_file": media_file,
				}
		elif media_type == "video":
			# If subtitles are enabled, use the VLC source
			if subtitle_track is not None:
				input_kind = "vlc_source"
				input_setting = {
					"playlist": [
						{
						"value": media_file,
						"selected": False,
						"hidden": False,
						}],
					"loop": False,
					"subtitle_enable": True,
					"subtitle": subtitle_track,
					}
			# Otherwise use the FFmpeg source which seems to be more stable
			else:
				input_kind = "ffmpeg_source"
				input_setting = {
					"local_file": media_file,
					}
		elif media_type == "image":
			input_kind = "image_source"
			input_setting = {
				"file": media_file,
				}
		elif media_type == "web":
			input_kind = "browser_source"
			input_setting = {
				"url": media_file,
				"width": 1280,
				"height": 720,
				"css": "",
				}
		elif media_type == "pdf":
			input_kind = "browser_source"
			input_setting = {
				"is_local_file": True,
				"local_file": media_file,
				"width": 1280,
				"height": 720,
				"css": "",
				}
		else:
			raise AssertionError("Unsupported media_type: %s" % media_type)

		logger.info(" Input: %s \"%s\"", input_kind, input_name)
		logger.info(" Input settings: %s", input_setting)

		# Add a new scene. (Naming naming conflicts will be resolved.)
		scene_uuid = self.create_scene(
			scene_name,
			make_unique = True,
			pos = self.select_scene_pos(skiplist=skiplist),
			)["sceneUuid"]

		# If there is a thumbnail image, insert it behind the main media.
		if thumbnail is not None:
			thumbnail_source = self.create_unique_input(
				scene_uuid = scene_uuid,
				input_name = os.path.basename(thumbnail),
				input_kind = "image_source",
				input_settings = {"file": thumbnail},
				)
			self.set_scene_item_private_settings(scene_uuid, thumbnail_source["sceneItemId"], {
				"color":"",
				"color-preset": 8,		# grey
				})
			self.scale_scene_item(scene_uuid, thumbnail_source["sceneItemId"])

		# Create an input (a kind of source) to play our file.
		source = self.create_unique_input(
			scene_uuid = scene_uuid,
			input_name = input_name,
			input_kind = input_kind,
			input_settings = input_setting,
			)
		self.set_scene_item_private_settings(scene_uuid, source["sceneItemId"], {
			"color":"",
			"color-preset": 6,			# purple
			})

		if media_type != "audio":
			self.scale_scene_item(scene_uuid, source["sceneItemId"])

		# Enable audio monitoring for video files
		if media_type in ("video", "audio"):
			self.request("SetInputAudioMonitorType", {
				"inputUuid": source["inputUuid"],
				"monitorType": "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT",
				})

	#============================================================================
	# Create input sources of various types
	#============================================================================

	# Create the specified OBS input and add it as a scene item to the specified scene.
	# If the input already exists, reuse it and add it as a scene item to the specified scene.
	# We use this for cameras and screen captures.
	def create_input_with_reuse(self, scene_uuid, input_name, input_kind, input_settings):
		scene_item_id = None
		try:
			result = self.create_input(
				scene_uuid = scene_uuid,
				input_name = input_name,
				input_kind = input_kind,
				input_settings = input_settings,
				)
			scene_item_id = result["sceneItemId"]
		except ObsError as e:
			if e.code != 601:
				raise(ObsError(e))
			scene_item_id = self.create_scene_item(
				scene_uuid = scene_uuid,
				source_name = input_name,
				)
		return scene_item_id

	# Create the specified OBS input and add it as a scene item to the specified scene.
	# If an input with the specified name already exists, permutate the name until it is unique.
	def create_unique_input(self, scene_uuid, input_name, input_kind, input_settings):
		result = None
		i = 1
		while True:
			try_input_name = input_name
			if i == 1:
				try_input_name = input_name
			else:
				try_input_name = f"{input_name} ({i})"
			try:
				result = self.create_input(
					scene_uuid = scene_uuid,
					input_name = try_input_name,
					input_kind = input_kind,
					input_settings = input_settings,
					)
				break
			except ObsError as e:
				if e.code != 601:		# resource already exists
					raise ObsError(e)
			i += 1
		return result

	def add_existing_source(self, scene_uuid, source_name):
		"""Add an existing OBS source to a scene"""
		scene_item_id = self.create_scene_item(
			scene_uuid = scene_uuid,
			source_name = source_name,
			)
		return scene_item_id

	def add_camera_source(self, scene_uuid, camera):
		"""
		Create an OBS source for the specified camera, if it does not
		exist already, and add it to the specified scene.
		"""
		camera_name, input_kind, device_id = camera
		if input_kind == "dshow_input":			# Windows
			input_settings = {
				"video_device_id": device_id,
				}
		else:									# Linux
			input_settings = {
				"device_id": device_id,
				"input": 0,
				"pixelformat": 1196444237,		# Motion-JPEG
				#"pixelformat": 875967048,		# H.264
				#"pixelformat" : 1448695129,	# YUYV 4:2:2
				"resolution": 83886800,			# 1280x720
				"framerate": 4294967326,		# 30 fps
				"auto_reset": True,
				"timeout_frames": 30,			# Default of 5 is too short for some cameras, leads to continuous restarts
				"buffering": False,
				}
		scene_item_id = self.create_input_with_reuse(
			scene_uuid = scene_uuid,
			input_name = camera_name,
			input_kind = input_kind,
			input_settings = input_settings,
			)
		return scene_item_id

	def add_capture_source(self, scene_uuid, capture_window):
		"""
		Create an OBS source which captures the specified window, if it does
		not exist already, and add it to the specified scene.
		"""
		scene_item_id = self.create_input_with_reuse(
			scene_uuid = scene_uuid,
			input_name = "Second Zoom Window",
			input_kind = "xcomposite_input",
			input_settings = {
				"show_cursor": False,
				"capture_window": capture_window,
				}
			)
		return scene_item_id

	def add_remote_source(self, scene_uuid, settings):
		"""Add a browser source displaying the VDO.Ninja site"""
		scene_item_id = self.create_input_with_reuse(
			scene_uuid = scene_uuid,
			input_name = "VDO.Ninja %s" % settings.get("view"),
			input_kind = "browser_source",
			input_settings = {
				"url": "https://vdo.ninja?%s" % urlencode(settings),
				"width": 1280,
				"height": 720,
				"reroute_audio": True,
				"webpage_control_level": 0,
				}
			)
		return scene_item_id

	def add_source(self, scene_uuid, scheme, address):
		"""Fork out to the other add_*_source functions"""
		if scheme == "camera":
			return self.add_camera_source(scene_uuid, address)
		if scheme == "window":
			return self.add_capture_source(scene_uuid, address)
		elif scheme == "existing":
			return self.add_existing_source(scene_uuid, address)
		elif scheme == "remote":
			return self.add_remote_source(scene_uuid, address)
		raise ValueError(f"unrecognized scheme: {scheme}")

	#============================================================================
	# Create scenes with sources
	#============================================================================

	def create_source_scene(self, scene_name, source_scheme, source_address):
		"""Create a scene containing a single source"""
		pos = self.select_scene_pos(skiplist="*")
		scene_uuid = self.create_scene(scene_name, make_unique=True, pos=pos)["sceneUuid"]
		scene_item_id = self.add_source(scene_uuid, source_scheme, source_address)
		self.scale_scene_item(scene_uuid, scene_item_id)

	def create_split_scene(self, scene_name, left_scheme, left_address, right_scheme, right_address):
		"""Create a scene containing the two indicated sources"""
		pos = self.select_scene_pos(skiplist="*")
		scene_uuid = self.create_scene(scene_name, make_unique=True, pos=pos)["sceneUuid"]

		# Left side
		scene_item_id = self.add_source(scene_uuid, left_scheme, left_address)
		self.scale_scene_item(scene_uuid, scene_item_id, {
			"boundsHeight": 360.0,
			"boundsWidth": 640.0,
			"positionX": 0.0,
			"positionY": 160.0,
			})

		# Right Side
		scene_item_id = self.add_source(scene_uuid, right_scheme, right_address)
		self.scale_scene_item(scene_uuid, scene_item_id, {
			"boundsHeight": 360.0,
			"boundsWidth": 640.0,
			"positionX": 640.0,
			"positionY": 160.0,
			})

	def scale_scene_item(self, scene_uuid, scene_item_id, scene_item_transform=None):
		xform = {
			"boundsAlignment": 0,
			"boundsWidth": 1280,
			"boundsHeight": 720,
			"boundsType": "OBS_BOUNDS_SCALE_INNER",
			}
		if scene_item_transform is not None:
			xform.update(scene_item_transform)
		self.set_scene_item_transform(scene_uuid, scene_item_id, xform)
