from flask import current_app

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

# Load a client API for controlling OBS. At one point we had two version of it:
# * obs_api.py was used when we were running inside OBS.
#   It worked using the OBS script API.
# * obs_ws_5.py was used when we are running outside OBS.
#   It communicates with OBS through the OBS Websocket plugin.
#
# At the moment though, obs_ws_5.py is the only one in working order.

#try:
#	from .obs_api import ObsControl, ObsError
#except ModuleNotFoundError:
#	from .obs_ws_5 import ObsControl, ObsError

from .obs_ws_5 import ObsControl, ObsError

obs = ObsControl(config=current_app.config.get("OBS_WEBSOCKET"))

