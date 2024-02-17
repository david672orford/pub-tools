# Reimplementation of Turbo-Flask using Server Side Events instead of Websocket
# https://turbo-flask.readthedocs.io/en/latest/index.html

from flask import request, Response
from markupsafe import Markup
import queue
import logging

logger = logging.getLogger(__name__)

class Turbo:
	def __init__(self, app=None):
		self.user_id_callback = None
		if app:
			self.init_app(app)
		self.clients = {}

		# Define the functions which create Turbo Stream messages
		template = '<turbo-stream action="{action}" target="{target}"><template>{content}</template></turbo-stream>'
		for action in ('append', 'prepend', 'replace', 'update', 'remove', 'after', 'before'):
			def make_formatter(action):
				t = template.replace("{action}", action)
				def formatter(content, target):
					return t.format(content=content, target=target)
				return formatter
			setattr(self, action, make_formatter(action))

	def init_app(self, app):

		# The EventSource in the web page connects to this
		@app.route("/turbo-sse")
		def turbo_stream():
			client_id = self.user_id_callback()
			logger.debug("EventStream from %s connected" % client_id)
			if not client_id in self.clients:
				self.clients[client_id] = queue.Queue(maxsize=10)
			client_queue = self.clients[client_id]
			def stream():
				yield "retry: 5000\n"
				while True:
					data = client_queue.get()
					logger.debug("Pull message: %s %s", client_id, data)
					yield "data: " + data.replace("\n", " ") + "\n\n"
			return Response(stream(), mimetype="text/event-stream")	

		# Define a Jinja2 macro which generates Javascript code to load Hotwire Turbo
		# and connect it to the event source route /turbo-sse defined above.
		def turbo():
			url = "https://cdn.jsdelivr.net/npm/@hotwired/turbo@7.2.2/dist/turbo.es2017-umd.js"
			return Markup('''
				<script src="{url}"></script>
				<script>Turbo.connectStreamSource(new EventSource("/turbo-sse"));</script>
				''').format(url=url)
		app.context_processor(lambda: {'turbo': turbo})

	# Decorator which caller uses to provide a function which sets the ID number
	# of the SSE connection. Page code can then send messages to that client by
	# using the same ID in the to parameter to push().
	def user_id(self, callback):
		self.user_id_callback = callback
		return callback

	def turbo_frame(self):
		return request.headers.get("Turbo-Frame")

	def can_stream(self):
		return "text/vnd.turbo-stream.html" in request.accept_mimetypes

	def can_push(self, to=None):
		return to in self.clients

	def stream(self, stream):
		return Response(stream, mimetype="text/vnd.turbo-stream.html")

	# Queue a Turbo Stream message for delivery to a client
	def push(self, message, to=None):
		logger.debug("Push message: %s %s", to, message)
		for client in self.clients.keys() if to is None else [to]:
			try:
				self.clients[client].put_nowait(message)
			except queue.Full:
				logger.info("EventStream client %s disconnected" % client)
				del self.clients[client]

