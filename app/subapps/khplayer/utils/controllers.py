import os
import sys
from flask import current_app
import json

#=============================================================================
# For fetching articles and media files from JW.ORG
#=============================================================================

from ....jworg.meetings import MeetingLoader

meeting_loader = MeetingLoader(
	language = current_app.config["PUB_LANGUAGE"],
	cachedir = current_app.config["MEDIA_CACHEDIR"],
	debuglevel = 0,
	)

#=============================================================================
# For communication with OBS Studio
#=============================================================================

from .obs_control import ObsControl, ObsError

obs_config = current_app.config.get("OBS_WEBSOCKET")
if obs_config is None:
	if sys.platform == "win32":
		obs_websocket_configfile = os.path.join(os.environ["APPDATA"], "obs-studio", "plugin_config", "obs-websocket", "config.json")
	else:
		obs_websocket_configfile = os.path.join(os.environ["HOME"], ".config", "obs-studio", "plugin_config", "obs-websocket", "config.json")
	if os.path.exists(obs_websocket_configfile):
		with open(obs_websocket_configfile) as fh:
			obs_websocket_config = json.load(fh)

		obs_config = {
			"hostname": "localhost",
			"port": obs_websocket_config["server_port"],
			"password": obs_websocket_config["server_password"],
			"obs_websocket_enabled": obs_websocket_config["server_enabled"],
			}

obs = ObsControl(config = obs_config)

def init_app(app):
	obs.app = app
