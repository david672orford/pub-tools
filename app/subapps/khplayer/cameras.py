import os
from glob import glob

# List the available cameras by device node and descriptive name
def list_cameras():
	for dev in glob("/sys/class/video4linux/*"):
		with open(os.path.join(dev, "name")) as fh:
			name = fh.read().strip()
		with open(os.path.join(dev, "index")) as fh:
			index = int(fh.read().strip())
		if index == 0:
			yield ("/dev/" + os.path.basename(dev), name)

