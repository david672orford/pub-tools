import os, sys
import argparse
import logging

from obs2zoom.obs_ws import ObsEventReader
from obs2zoom.policies import ObsToZoomManual, ObsToZoomAuto
from obs2zoom.zoom import ZoomControl

def main():
	parser = argparse.ArgumentParser(description="Automatically stop and start sharing of OBS virtual camera in Zoom")
	parser.add_argument("--auto", dest="auto_mode", action="store_true", help="share screen when vcam on and media playing")
	parser.add_argument("--manual", dest="auto_mode", action="store_false", help="share screen when vcam on")
	options = parser.parse_args()

	try:
		obs = ObsEventReader()
	except ConnectionRefusedError:
		sys.stderr.write("%s: OBS-Websocket not running\n" % sys.argv[0])
		sys.exit(1)

	zoom = ZoomControl()

	if options.auto_mode:
		policy = ObsToZoomAuto(obs, zoom)
	else:
		policy = ObsToZoomManual(obs, zoom)

	while policy.handle_message():
		pass

