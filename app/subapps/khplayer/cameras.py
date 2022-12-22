from flask import current_app
import os
from glob import glob

def list_cameras():
	for dev in glob("/sys/class/video4linux/*"):
		with open(os.path.join(dev, "name")) as fh:
			name = fh.read().strip()
		with open(os.path.join(dev, "index")) as fh:
			index = int(fh.read().strip())
		if index == 0:
			yield ("/dev/" + os.path.basename(dev), name)

def camera_dev_lookup(camera_name):
	for dev_node, display_name in list_cameras():
		if display_name == camera_name:
			return dev_node
	return None

def get_camera_dev():
	camera = current_app.config.get("PERIPHERALS",{}).get("camera")
	if camera is None:
		flash("No camera selected in configuration")
	camera_dev = camera_dev_lookup(camera)
	if camera_dev is None:
		flash("Camera not connected: %s" % camera)
	return camera_dev
