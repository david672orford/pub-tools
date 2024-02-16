import os, re
from urllib.parse import urlparse, unquote
import logging

logger = logging.getLogger(__name__)

#try:
#	from .obs_api import ObsControl, ObsError
#except ModuleNotFoundError:
#	from .obs_ws_5 import ObsControl, ObsError

from .obs_ws_5 import ObsControlBase, ObsError

class ObsControl(ObsControlBase):

	# Create a scene for a video or image file.
	# Center it and scale to reach the edges.
	# For videos enable audio monitoring.
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

		# FIXME: Hopefully we can use this in future
		if thumbnail_url is not None:
			source_settings["thumbnail_url"] = thumbnail_url

		logger.info(" Source: %s \"%s\"", source_type, source_name)
		logger.info(" Source settings: %s", source_settings)

		# Add a new scene. (Naming naming conflicts will be resolved.)
		scene_name = self.create_scene(scene_name, make_unique=True)

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

		if media_type != "audio":
			self.scale_input(scene_name, scene_item_id)

		# Enable audio monitoring for video files
		if media_type == "video":
			payload = {
				'inputName': source_name,
				'monitorType': "OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT",
				}
			self.request('SetInputAudioMonitorType', payload)

	# Create the specified OBS input, if it does not exist already,
	# and add it to the specified scene.
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

	# Create an OBS input for the configured camera, if it does not exist already,
	# and add it to the specified scene.
	def add_camera_input(self, scene_name, camera_dev):
		camera_dev, camera_name = camera_dev.split(" ",1)
		scene_item_id = self.create_input_with_reuse(
			scene_name = scene_name,
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
	def add_zoom_input(self, scene_name, capture_window):
		scene_item_id = self.create_input_with_reuse(
			scene_name = scene_name,
			input_name = "%s Capture" % capture_window,
			input_kind = "xcomposite_input",
			input_settings = {
				"show_cursor": False,
				"capture_window": capture_window,
				}
			)
		return scene_item_id

	# Create a scene containing just the specified camera
	def create_camera_scene(self, scene_name, camera_dev):
		scene_name = self.create_scene(scene_name, make_unique=True)
		scene_item_id = self.add_camera_input(scene_name, camera_dev)
		#self.scale_input(scene_name, scene_item_id)

	# Create a scene containing just a capture of the specified window
	def create_zoom_scene(self, scene_name, capture_window):
		scene_name = self.create_scene(scene_name, make_unique=True)
		scene_item_id = self.add_zoom_input(scene_name, capture_window)
		self.scale_input(scene_name, scene_item_id)

	# Create a scene with the specified camera on the left and a capture of the specified window on the right
	def create_split_scene(self, scene_name, camera_dev, capture_window):
		scene_name = self.create_scene(scene_name, make_unique=True)

		# Camera on left side
		scene_item_id = self.add_camera_input(scene_name, camera_dev)
		self.scale_input(scene_name, scene_item_id, {
			"boundsHeight": 360.0,
			"boundsWidth": 640.0,
			"positionX": 0.0,
			"positionY": 160.0,
			})

		# Zoom on right side
		scene_item_id = self.add_zoom_input(scene_name, capture_window)
		self.scale_input(scene_name, scene_item_id, {
			"boundsHeight": 360.0,
			"boundsWidth": 640.0,
			"positionX": 640.0,
			"positionY": 160.0,
			})

