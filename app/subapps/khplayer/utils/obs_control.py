import os, re
from urllib.parse import urlparse, unquote
import logging

logger = logging.getLogger(__name__)

#try:
#	from .obs_api import ObsControl, ObsError
#except ModuleNotFoundError:
#	from .obs_ws_5 import ObsControl, ObsError

from .obs_ws_5 import ObsControlBase, ObsError
from ....utils.config import get_config, put_config

class ObsControl(ObsControlBase):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.scene_list = None

	#============================================================================
	# OBS-Websocker provides no way to reorder scene or control the position
	# of new scenes. For this reason we maintain or own scene order and
	# wrap .get_scene_list().
	#============================================================================

	def get_scene_list(self):
		if self.scene_list is None:
			self.scene_list = super().get_scene_list()

			# Restore our saved scene order. New scenes go at the end.
			scenes = []
			for scene_uuid in get_config("SCENE_ORDER", []):
				try:
					scenes.append(self.scene_list["scenes"].pop(self.scene_index(scene_uuid)))
				except KeyError:
					pass
			for scene in self.scene_list["scenes"]:
				scenes.append(scene)
			self.scene_list["scenes"] = scenes

			self.subscribe("scenes", lambda event: self.event(event))
		return self.scene_list

	def event(self, event):
		data = event["eventData"]
		match event["eventType"]:
			case "SceneCreated":
				self.scene_list["scenes"].append(data)
				#self.save_scene_order()
			case "SceneRemoved":
				self.scene_list["scenes"].pop(self.scene_index(data["sceneUuid"]))
				#self.save_scene_order()
			case "SceneNameChanged":
				self.scene_list["scenes"][self.scene_index(uuid)]["sceneName"] = data["sceneName"]
			case "CurrentProgramSceneChanged":
				self.scene_list["currentProgramSceneUuid"] = data["sceneUuid"]
				self.scene_list["currentProgramSceneName"] = data["sceneName"]
			case "CurrentPreviewSceneChanged":
				self.scene_list["currentPreviewSceneUuid"] = data["sceneUuid"]
				self.scene_list["currentPreviewSceneName"] = data["sceneName"]

	def scene_index(self, uuid):
		scenes = self.get_scene_list()["scenes"]
		for i in range(len(scenes)):
			if scenes[i]["sceneUuid"] == uuid:
				return i
		raise KeyError()

	def move_scene(self, uuid, new_index):
		i = self.scene_index(uuid)
		scene = self.scene_list["scenes"].pop(i)
		self.scene_list["scenes"].insert(new_index, scene)
		self.save_scene_order()

	def save_scene_order(self):
		uuids = []
		for scene in self.get_scene_list()["scenes"]:
			uuids.append(scene["sceneUuid"])
		put_config("SCENE_ORDER", uuids)

	#============================================================================
	# Create a scene for a video or image file.
	# Center it and scale to reach the edges.
	# For videos enable audio monitoring.
	#============================================================================
	def add_media_scene(self, scene_name, media_type, media_file, thumbnail_url=None, subtitle_track=None):
		logger.info("Add media_scene: \"%s\" %s \"%s\"", scene_name, media_type, media_file)

		# Get basename of media file
		if re.match(r"^https?://", media_file, re.I):
			parsed_url = urlparse(media_file)
			path = parsed_url.path
			if path == "":
				source_name = parsed_url.hostname
			elif path.endswith("/"):
				source_name = path.split("/")[-2]
			else:
				source_name = path.split("/")[-1]
			source_name = unquote(source_name)
		else:
			source_name = os.path.basename(media_file)

		# Select the appropriate OBS source type and build its settings
		if media_type == "audio":
			source_type = "ffmpeg_source"
			source_settings = {
				"local_file": media_file,
				}
		elif media_type == "video":
			# If subtitles are enabled, use the VLC source
			if subtitle_track is not None:
				source_type = "vlc_source"
				source_settings = {
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
				source_type = "ffmpeg_source"
				source_settings = {
					"local_file": media_file,
					}
		elif media_type == "image":
			source_type = "image_source"
			source_settings = {
				"file": media_file,
				}
		elif media_type == "web":
			source_type = "browser_source"
			source_settings = {
				"url": media_file,
				"width": 1280, "height": 720,
				"css": "",
				}
		else:
			raise AssertionError("Unsupported media_type: %s" % media_type)

		# FIXME: Remove if we don't find a way to use this
		if thumbnail_url is not None:
			source_settings["thumbnail_url"] = thumbnail_url

		logger.info(" Source: %s \"%s\"", source_type, source_name)
		logger.info(" Source settings: %s", source_settings)

		# Add a new scene. (Naming naming conflicts will be resolved.)
		scene_uuid = self.create_scene(scene_name, make_unique=True)["sceneUuid"]

		# Create a source (now called an input) to play our file. Resolve naming conflicts.
		i = 1
		scene_item_id = None
		while True:
			try_source_name = source_name
			if i == 1:
				try_source_name = source_name
			else:
				try_source_name = f"{source_name} ({i})"
			payload = {
				'sceneUuid': scene_uuid,
				'inputName': try_source_name,
				'inputKind': source_type,
				'inputSettings': source_settings,
				}
			try:
				response = create_input(scene_uuid, try_source_name, source_type, source_settings)
				source_name = try_source_name
				scene_item_id = response["sceneItemId"]
				break
			except ObsError as e:
				if e.code != 601:		# resource already exists
					raise ObsError(e)
			i += 1

		if media_type != "audio":
			self.scale_scene_item(scene_uuid, scene_item_id)

		# Enable audio monitoring for video files
		if media_type == "video":
			payload = {
				'inputName': source_name,
				'monitorType': "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT",
				}
			self.request('SetInputAudioMonitorType', payload)

	#============================================================================
	# Create inputs
	#============================================================================

	# Create the specified OBS input, if it does not exist already,
	# and add it to the specified scene.
	def create_input_with_reuse(self, scene_uuid, input_name, input_kind, input_settings):
		try:
			scene_item_id = self.create_input(
				scene_uuid = scene_uuid,
				input_name = input_name,
				input_kind = input_kind,
				input_settings = input_settings
				)
		except ObsError as e:
			if e.code != 601:
				raise(ObsError(e))
			scene_item_id = self.create_scene_item(
				scene_uuid = scene_uuid,
				source_name = input_name,
				)
		return scene_item_id

	# Create an OBS input for the configured camera, if it does not exist already,
	# and add it to the specified scene.
	def add_camera_input(self, scene_uuid, camera_dev):
		camera_dev, camera_name = camera_dev.split(" ",1)
		scene_item_id = self.create_input_with_reuse(
			scene_uuid = scene_uuid,
			input_name = camera_name,
			input_kind = "v4l2_input",
			input_settings = {
				"device_id": camera_dev,
				"input": 0,
				"pixelformat": 1196444237,		# Motion-JPEG
				#"pixelformat": 875967048,		# H.264
				#"pixelformat" : 1448695129,	# YUYV 4:2:2
				"resolution": 83886800,			# 1280x720
				"auto_reset": True,
				"buffering": False,
				}
			)
		return scene_item_id

	# Create an OBS input which captures the specified window, if it does
	# not exist already, and add it to the specified scene.
	def add_zoom_input(self, scene_uuid, capture_window):
		scene_item_id = self.create_input_with_reuse(
			scene_uuid = scene_uuid,
			input_name = "%s Capture" % capture_window,
			input_kind = "xcomposite_input",
			input_settings = {
				"show_cursor": False,
				"capture_window": capture_window,
				}
			)
		return scene_item_id

	#============================================================================
	# Create standard scenes
	#============================================================================

	def scale_scene_item(self, scene_uuid, scene_item_id, scene_item_transform={}):
		xform = {
			'boundsAlignment': 0,
			'boundsWidth': 1280,
			'boundsHeight': 720,
			'boundsType': 'OBS_BOUNDS_SCALE_INNER',
			}
		xform.update(scene_item_transform)
		self.set_scene_item_transform(scene_uuid, scene_item_id, xform)

	# Create a scene containing just the specified camera
	def create_camera_scene(self, scene_name, camera_dev):
		scene_uuid = self.create_scene(scene_name, make_unique=True)["sceneUuid"]
		scene_item_id = self.add_camera_input(scene_uuid, camera_dev)
		#self.scale_scene_item(scene_uuid, scene_item_id)

	# Create a scene containing just a capture of the specified window
	def create_zoom_scene(self, scene_name, capture_window):
		scene_uuid = self.create_scene(scene_name, make_unique=True)["sceneUuid"]
		scene_item_id = self.add_zoom_input(scene_uuid, capture_window)
		self.scale_scene_item(scene_uuid, scene_item_id)

	# Create a scene with the specified camera on the left and a capture of the specified window on the right
	def create_split_scene(self, scene_name, camera_dev, capture_window):
		scene_uuid = self.create_scene(scene_name, make_unique=True)["sceneUuid"]

		# Camera on left side
		scene_item_id = self.add_camera_input(scene_uuid, camera_dev)
		self.scale_scene_item(scene_uuid, scene_item_id, {
			"boundsHeight": 360.0,
			"boundsWidth": 640.0,
			"positionX": 0.0,
			"positionY": 160.0,
			})

		# Zoom on right side
		scene_item_id = self.add_zoom_input(scene_uuid, capture_window)
		self.scale_scene_item(scene_uuid, scene_item_id, {
			"boundsHeight": 360.0,
			"boundsWidth": 640.0,
			"positionX": 640.0,
			"positionY": 160.0,
			})

