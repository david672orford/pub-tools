"""Clients for interaction with OBS and JW.ORG"""

from flask import current_app

#=============================================================================
# Web clinet for fetching articles and media files from JW.ORG
#=============================================================================

from ....jworg.meetings import MeetingLoader

meeting_loader = MeetingLoader(
	language = current_app.config["PUB_LANGUAGE"],
	cachedir = current_app.config["MEDIA_CACHEDIR"],
	debuglevel = 0,
	)

#=============================================================================
# OBS-Websocket client for controlling OBS Studio
#=============================================================================

from .obs_control import ObsControl, ObsError
from .obs_config import ObsConfig

# Read connection parameters for OBS-Websocket from config.py.
# Fall back to parameters read directly from OBS config file.
obs_websocket_config = current_app.config.get("OBS_WEBSOCKET")
if obs_websocket_config is None:
	obs_config = ObsConfig()
	obs_websocket_config = obs_config.websocket_config()

# Create the OBS-Websocket client
obs = ObsControl(config = obs_websocket_config)

# Client sometimes needs to create an app context so it can call put_config().
def init_app(app):
	obs.init_app(app)
