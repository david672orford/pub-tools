# Run downloads in a background thread

from flask import current_app, session, copy_current_request_context, flash as regular_flash
from threading import Thread, current_thread
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
		flash(_("Please wait for previous download to finish."))

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
			turbo.push(turbo.append(message, target="progress-message"), to=to)
	except KeyError:
		logger.warning("No Turbo connection from client: %s", to)

# Send an update to the web browser in response to a form submission.
def progress_response(message, last_message=False, **kwargs):
	if message is None:
		message = ""
	else:
		message = message.format(**kwargs)
	message = turbo.append('<div>%s</div>%s' % (
		escape(message),
		"<script>hide_progress()</script>" if last_message else "",
		), target="progress-message")
	return turbo.stream(message)

# Version of Flask's flash() which sends the flash using Turbo,
# if it is called from the background thread.
def flash(message: str, category: str="message") -> None:
	if current_thread() is background_thread:
		to = session['session-id']
		turbo.push(turbo.append('<div class="flash">%s</div>' % escape(message), target="flashes"), to=to)
	else:
		regular_flash(message, category=category)

