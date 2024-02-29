from flask import current_app
import json

#=============================================================================
# For fetching articles and media files from JW.ORG
#=============================================================================

from ....jworg.meetings import MeetingLoader

meeting_loader = MeetingLoader(
	cachedir = current_app.config["MEDIA_CACHEDIR"],
	debuglevel = 0,
	)

#=============================================================================
# For communication with OBS Studio
#=============================================================================

from .obs_control import ObsControl, ObsError

obs = ObsControl(
	config = current_app.config.get("OBS_WEBSOCKET"),
	)

def init_app(app):
	obs.app = app

