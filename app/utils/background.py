from flask import current_app, session, copy_current_request_context
from threading import Thread
from markupsafe import escape
import logging

from .babel import gettext as _
#from turbo_flask import Turbo
from .turbo_sse import Turbo

logger = logging.getLogger(__name__)

turbo = Turbo()

# Start a background downloader
background_thread = None
def run_thread(func):
	global background_thread

	if background_thread is not None and background_thread.is_alive():
		async_flash(_("Please wait for previous download to finish."))

	@copy_current_request_context
	def wrapper():
		func()

	background_thread = Thread(target=wrapper, daemon=True)
	background_thread.start()

# Send an asyncronous status update to the web browser
def progress_callback(message, last_message=False, **kwargs):
	to = session['session-id']
	try:
		if message == "{total_recv} of {total_expected}":
			percent = int(kwargs["total_recv"]  * 100 / kwargs["total_expected"] + 0.5)
			message = '<div style="width: {percent}%"></div>'.format(percent=percent)
			turbo.push(turbo.update(message, target="progress-bar"), to=to)
		else:
			message = message.format(**kwargs)
			message = '<div>%s</div>%s' % (
				escape(message),
				"<script>hide_progress()</script>" if last_message else "",
				)
			turbo.push(turbo.update(message, target="progress-message"), to=to)
	except KeyError:
		logger.warning("No Turbo connection from client: %s", to)

# Send a syncronous status update to the web browser in response to a form submission
def progress_response(message, last_message=False, **kwargs):
	message = message.format(**kwargs)
	return turbo.stream([
		turbo.update('<div>%s</div>%s' % (
			escape(message),
			"<script>hide_progress()</script>" if last_message else "",
			), target="progress-message")
		])

# Asyncronous version of Flask's flash() for use in background download threads
def async_flash(message):
	to = session['session-id']
	turbo.push(turbo.append('<div class="progress flash">%s</div>' % escape(message), target="flashes"), to=to)

