# Send updated chunks of HTML to the client where they will be received by
# Hotwire's Turbo library. 

from flask import session
#from turbo_flask import Turbo
from .turbo_sse import Turbo
import logging
from . import app

logger = logging.getLogger(__name__)

turbo = Turbo()
turbo.init_app(app)

@app.before_request
def set_sessionid():
	if not "session-id" in session:
		session["session-id"] = uuid.uuid4().hex
	print("Session ID:", session["session-id"])

@turbo.user_id
def get_session_id():
	return session["session-id"]

