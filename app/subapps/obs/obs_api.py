# Add a scene with a single media item to OBS
# This version uses the OBS Script API

import obspython as obs
from urllib.parse import urlparse, unquote
import os
import json
import re
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class ObsControl:
	def __init__(self):
		self.queue = []

	def add_scene(self, scene_name, media_type, media_file):
		logger.info("Add scene: \"%s\" %s \"%s\"", scene_name, media_type, media_file)

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
		source_settings = obs.obs_data_create()
		if media_type == "video":
			source_type = "ffmpeg_source"
			obs.obs_data_set_string(source_settings, 'local_file', media_file)
		elif media_type == "image":
			source_type = "image_source"
			obs.obs_data_set_string(source_settings, 'file', media_file)
		elif media_type == "web":
			source_type = "browser_source"
			obs.obs_data_set_string(source_settings, 'url', media_file)
			obs.obs_data_set_int(source_settings, 'width', 1280)
			obs.obs_data_set_int(source_settings, 'height', 720)
			obs.obs_data_set_string(source_settings, 'css', '')
		else:
			raise AssertionError("Unsupported media_type: %s" % media_type)

		# Create a new scene. Naming conflicts resolved automatically.
		scene = obs.obs_scene_create(scene_name)

		# Create a source to play our file. Naming conflicts resolved automatically.
		source = obs.obs_source_create(source_type, source_name, source_settings, None)

		# Add the source to the scene creating a scene item.
		scene_item = obs.obs_scene_add(scene, source)

		# Make the video fill the screen
		obs.obs_sceneitem_set_bounds_type(scene_item, obs.OBS_BOUNDS_SCALE_INNER)
		bounds = obs.vec2()
		obs.obs_sceneitem_get_bounds(scene_item, bounds)
		bounds.x = 1280
		bounds.y = 720
		obs.obs_sceneitem_set_bounds(scene_item, bounds)
		obs.obs_sceneitem_set_bounds_alignment(scene_item, 0)

		# Enable audio for video files
		if media_type == "video":
			obs.obs_source_set_monitoring_type(source, obs.OBS_MONITORING_TYPE_MONITOR_AND_OUTPUT)

		obs.obs_scene_release(scene)
		obs.obs_data_release(source_settings)
		obs.obs_source_release(source)

