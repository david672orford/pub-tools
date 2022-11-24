from flask import session, flash
from time import sleep
from threading import Thread
from markupsafe import escape
import uuid
import logging

from ... import app, turbo
from ...jworg.meetings import MeetingLoader

logger = logging.getLogger(__name__)

#=============================================================================
# For fetching articles and media files from JW.ORG
#=============================================================================

meeting_loader = MeetingLoader(cachedir=app.cachedir)

#=============================================================================
# Communication with OBS Studio
#=============================================================================

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

#=============================================================================
# Run a background process in a thread
#=============================================================================

def run_thread(func):
	thread = Thread(target=func)
	thread.daemon = True
	thread.start()

#=============================================================================
# Send updated chunks of HTML to the client using Turbo-Flask
#=============================================================================

@turbo.user_id
def get_session_id():
	if not "session-id" in session:
		session["session-id"] = uuid.uuid1().hex
	print("Session ID:", session["session-id"])
	return session["session-id"]

def _progress_callback(to, message, kwargs):
	message = message.format(**kwargs)
	try:
		turbo.push(turbo.replace('<div id="progress">%s</div>' % escape(message), target="progress"), to=to)
	except KeyError:
		logger.warning("Turbo web socket not connected:", to)

def make_progress_callback():
	to = get_session_id()
	def progress_callback_wrapper(message, **kwargs):
		_progress_callback(to, message, kwargs)
	return progress_callback_wrapper

