# Run a background job in a thread

from flask import session, copy_current_request_context
from threading import Thread
from markupsafe import escape
import logging

from . import turbo

logger = logging.getLogger(__name__)

background_thread = None
def run_thread(func):
	global background_thread

	if background_thread is not None and background_thread.is_alive():
		flask("Please wait for previous download to finish.")

	@copy_current_request_context
	def wrapper():
		func()

	background_thread = Thread(target=wrapper, daemon=True)
	background_thread.start()

def progress_callback(message, **kwargs):
	if message == "{total_recv} of {total_expected}":
		percent = int(kwargs["total_recv"]  * 100 / kwargs["total_expected"] + 0.5)
		message = '<div style="width: 200px; border: thin solid black"><div style="width: {percent}%; height: 20px; background-color: green"></div></div>'.format(percent=percent)
	else:
		message = message.format(**kwargs)
		message = '<div>%s</div>' % escape(message)
	to = session['session-id']
	try:
		turbo.push(turbo.update(message, target="progress"), to=to)
	except KeyError:
		logger.warning("No Turbo connection from client: %s", to)

def progress_callback_response(message, **kwargs):
	message = message.format(**kwargs)
	return turbo.stream([
		turbo.update('<div>%s</div>' % escape(message), target="progress")
		])

