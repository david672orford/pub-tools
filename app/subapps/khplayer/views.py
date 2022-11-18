# Views for loading media from JW.ORG into OBS

from flask import Blueprint, render_template, request, redirect, flash
from threading import Thread
from time import sleep
from markupsafe import escape
import logging

from ... import app, turbo
from ...jworg.meetings import MeetingLoader

logger = logging.getLogger(__name__)

blueprint = Blueprint("khplayer", __name__, template_folder="templates", static_folder="static")
blueprint.display_name = "KH Player"
blueprint.blurb = "Download videos and illustrations from JW.ORG and load them into OBS"

# Redirect to default tab
@blueprint.route("/")
def page_index():
	return redirect("meetings/")

# Whenever an uncaught exception occurs in a view function Flask returns
# HTTP error 500 (Internal Server Error). Here we catch this error so we
# can display a page with a reload link. We added this during development
# because we had trouble reloading OBS dockable webviews due to problems
# getting the necessary context menu to open.
@blueprint.errorhandler(500)
def handle_500(error):
	return render_template("khplayer/500.html", top=".."), 500

# For fetching articles and media files from JW.ORG
meeting_loader = MeetingLoader(cachedir=app.cachedir)

# Load a client API for controlling OBS. There are two versions of it.
# The first in obs_api.py works when we are running inside OBS. The
# second which is in obs_ws_N.py is what we use when we are running outside.
# It communicates with OBS through the OBS Websocket plugin.
try:
	from .obs_api import ObsControl
except ModuleNotFoundError:
	#from .obs_ws_4 import ObsControl
	from .obs_ws_5 import ObsControl, ObsError

# Page handlers call this to connect to OBS of it is not connected already.
def obs_connect(callback=flash):
	if not hasattr(obs_connect, "handle") or obs_connect.handle is None:
		if not "OBS_WEBSOCKET" in app.config:
			callback("Connexion to OBS not configured")
			return None
		try:
			obs_connect.handle = ObsControl(config=app.config["OBS_WEBSOCKET"])
			obs_connect.handle.connect()
		except ConnectionRefusedError:
			callback("Can't connect to OBS")
			obs_connect.handle = None
	return obs_connect.handle

# Run a background process in a thread
def run_thread(func):
	thread = Thread(target=func)
	thread.daemon = True
	thread.start()

def progress_callback(message, **kwargs):
	message = message.format(**kwargs)
	turbo.push(turbo.replace('<div id="progress">%s</div>' % escape(message), target="progress"))

from . import view_meetings
from . import view_songs
from . import view_videos
from . import view_stream
from . import view_obs

