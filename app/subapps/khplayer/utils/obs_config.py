"""Read and possibly modify the OBS configuration"""

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

	def websocket_config_filename(self):
		return os.path.join(self.obs_dir, "plugin_config", "obs-websocket", "config.json")

	def websocket_config(self):
		filename = self.websocket_config_filename()
		if os.path.exists(filename):
			with open(filename) as fh:
				obs_websocket_config = json.load(fh)
			return {
				"hostname": "localhost",
				"port": obs_websocket_config["server_port"],
				"password": obs_websocket_config["server_password"],
				"obs_websocket_enabled": obs_websocket_config["server_enabled"],
				}
		return None

	def enable_websocket(self):
		"""Enable the OBS-Websocket plugin"""
		filename = self.websocket_config_filename()
		temp_filename = f"{filename}.tmp"
		with open(filename) as fh:
			config = json.load(fh)
		config["server_enabled"] = True
		with open(temp_filename, "w") as fh:
			json.dump(config, fh, indent=4, ensure_ascii=False)
		self.safe_replace(filename, temp_filename)

	def config_filename(self):
		filename = os.path.join(self.obs_dir, "user.ini")
		if os.path.exists(filename):
			return filename
		return os.path.join(self.obs_dir, "global.ini")

	def get_config(self):
		config = ConfigParser(strict=False)
		config.optionxform = str
		config.read(self.config_filename())
		return config

	def save_config(self, config):
		filename = self.config_filename()
		temp_filename = f"{filename}.tmp"
		with open(temp_filename, "w") as fh:
			config.write(fh, space_around_delimiters=False)
		self.safe_replace(filename, temp_filename)

	def scenelist_filename(self, name):
		return os.path.join(self.obs_dir, "basic", "scenes", name.replace(" ","_") + ".json")

	def get_scene_collection(self, name):
		with open(self.scenelist_filename(name), "r", encoding="utf8") as fh:
			scenelist = json.load(fh)
		return scenelist

	def save_scene_collection(self, name, scene_collection):
		filename = self.scenelist_filename(name)
		temp_filename = f"{filename}.tmp"
		backup_filename = f"{filename}.bak"
		with open(temp_filename, "w", encoding="utf8") as fh:
			json.dump(scene_collection, fh, indent=4, ensure_ascii=False)
		self.safe_replace(filename, temp_filename, backup_filename)

	def safe_replace(self, filename, temp_filename, backup_filename=None):
		if backup_filename is not None:
			if os.path.exists(backup_filename):
				os.remove(backup_filename)
			os.rename(filename, backup_filename)
		os.replace(temp_filename, filename)
