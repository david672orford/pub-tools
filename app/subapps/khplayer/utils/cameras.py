import os
import sys

from flask import current_app

# Define a function which lists the available cameras by device node and descriptive name
try:
	# Implementation using the OBS API. Available only if server is embedded in OBS.
	import obspython as obs
	def list_cameras():
		name_overrides = current_app.config["CAMERA_NAME_OVERRIDES"]
		input_kind, property_name = {
			"linux": ("v4l2_input", "device_id"),
			"win32": ("dshow_input", "video_device_id"),
			}.get(sys.platform, (None, None))
		if input_kind is None:
			return []
		source = obs.obs_source_create_private(input_kind, "camera_lister", None)
		properties = obs.obs_source_properties(source)
		devices = obs.obs_properties_get(properties, property_name)
		for i in range(obs.obs_property_list_item_count(devices)):
			name = obs.obs_property_list_item_name(devices, i)
			value = obs.obs_property_list_item_string(devices, i)
			if name.startswith("OBS Virtual Camera"):
				continue
			yield (input_kind, value, name_overrides.get(name, name))
		obs.obs_properties_destroy(properties)
		obs.obs_source_release(source)
except ImportError:
	# Fallback implementation for V4L2 using the Linux /sys filesystem
	from glob import glob
	def list_cameras():
		name_overrides = current_app.config["CAMERA_NAME_OVERRIDES"]
		for dev in glob("/sys/class/video4linux/*"):
			with open(os.path.join(dev, "index")) as fh:
				index = int(fh.read().strip())
			if index > 0:
				continue
			with open(os.path.join(dev, "name")) as fh:
				name = fh.read().strip()
			if name == "OBS Virtual Camera":
				continue
			yield ("v4l2_input", "/dev/" + os.path.basename(dev), name_overrides.get(name, name))
