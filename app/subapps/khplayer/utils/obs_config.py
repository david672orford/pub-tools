"""OBS Configuration"""

import os
import sys
import json
from configparser import ConfigParser

class ObsConfig:
	def __init__(self):
		if sys.platform == "win32":
			self.obs_dir = os.path.join(os.environ["APPDATA"], "obs-studio")
		else:
			self.obs_dir = os.path.join(os.environ["HOME"], ".config", "obs-studio")

	def default_websocket_config(self):
		obs_websocket_configfile = os.path.join(self.obs_dir, "plugin_config", "obs-websocket", "config.json")
		if os.path.exists(obs_websocket_configfile):
			with open(obs_websocket_configfile) as fh:
				obs_websocket_config = json.load(fh)
			return {
				"hostname": "localhost",
				"port": obs_websocket_config["server_port"],
				"password": obs_websocket_config["server_password"],
				"obs_websocket_enabled": obs_websocket_config["server_enabled"],
				}
		return None
