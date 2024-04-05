from flask import current_app
import os
from glob import glob

# List the available cameras by device node and descriptive name
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

		yield ("/dev/" + os.path.basename(dev), name_overrides.get(name, name))

