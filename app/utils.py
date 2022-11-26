# Run a background job in a thread

from flask import session, copy_current_request_context
from threading import Thread
from markupsafe import escape
import logging

from . import turbo

logger = logging.getLogger(__name__)

def run_thread(func):
	@copy_current_request_context
	def wrapper():
		func()
	Thread(target=wrapper, daemon=True).start()

def progress_callback(message, **kwargs):
	to = session['session-id']
	message = message.format(**kwargs)
	try:
		turbo.push(turbo.replace('<div id="progress">%s</div>' % escape(message), target="progress"), to=to)
	except KeyError:
		logger.warning("No Turbo connection from client: %s", to)

