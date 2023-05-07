from flask import current_app, flash
from time import sleep
import logging

from ...jworg.meetings import MeetingLoader

logger = logging.getLogger(__name__)

#=============================================================================
# For fetching articles and media files from JW.ORG
#=============================================================================

meeting_loader = MeetingLoader(cachedir=current_app.config["CACHEDIR"])

#=============================================================================
# Communication with OBS Studio
#=============================================================================

# Load a client API for controlling OBS. There are two versions of it.
# The first in obs_api.py works when we are running inside OBS. The
# second which is in obs_ws_5.py is what we use when we are running outside.
# It communicates with OBS through the OBS Websocket plugin.
#try:
#	from .obs_api import ObsControl, ObsError
#except ModuleNotFoundError:
#	from .obs_ws_5 import ObsControl, ObsError

# For now only obs_ws_5 implements what we need
from .obs_ws_5 import ObsControl, ObsError

obs = ObsControl(config=current_app.config.get("OBS_WEBSOCKET"))

