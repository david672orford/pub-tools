# Run downloads in a background thread

from flask import current_app, session, copy_current_request_context, flash as flask_flash
from threading import Thread, current_thread
from markupsafe import escape
import traceback
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
		return

	@copy_current_request_context
	def wrapper():
		try:
			func()
		except Exception as e:
			logger.error(traceback.format_exc())
			flash(_("Error: %s") % str(e))
			progress_callback(_("Background task failed."), last_message=True)

	background_thread = Thread(target=wrapper, daemon=True)
	background_thread.start()

# Send an asyncronous status update to the web browser
def progress_callback(message, last_message=False, **kwargs):
	to = session["session-id"]
	try:
		if message == "{total_recv} of {total_expected}":
			percent = int(kwargs["total_recv"]  * 100 / kwargs["total_expected"] + 0.5)
			message = '<div style="width: {percent}%"></div>'.format(percent=percent)
			turbo.push(turbo.update(message, target="progress-bar"), to=to)
		else:
			turbo.push(format_progress_message(message, last_message=last_message, **kwargs), to=to)
	except KeyError:
		logger.warning("No Turbo connection from client: %s", to)

# Send an update to the web browser in response to a form submission.
def progress_response(message, last_message=False, **kwargs):
	logger.debug("Response message: %s", message)
	if message is None:		# empty message to prevent navigation
		return turbo.stream("")
	return turbo.stream(format_progress_message(message, last_message=last_message, **kwargs))

def format_progress_message(message, last_message=False, cssclass=None, **kwargs):
	message = message.format(**kwargs)
	message = "<div%s>%s</div>%s" % (
		f" class=\"{cssclass}\"" if cssclass is not None else "",
		escape(message),
		"<script>hide_progress()</script>" if last_message else "",
		) 
	return turbo.append(message, target="progress-message")

# Version of Flask's flash() which sends the flash using Turbo,
# if it is called from the background thread. Otherwise it calls
# through to the flash() function supplied by Flask.
def flash(message: str, category: str="message") -> None:
	if current_thread() is background_thread:
		async_flash(message, category=category)
	else:
		flask_flash(message, category=category)

def async_flash(message: str, category: str="message") -> None:
	to = session["session-id"]
	turbo.push(turbo.append('<div class="flash">%s</div>' % escape(message), target="flashes"), to=to)

