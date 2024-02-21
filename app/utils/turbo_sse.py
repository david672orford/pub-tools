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
				seq = 0
				while True:
					data = client_queue.get()
					logger.debug("Pull message: %s %s", client_id, data)
					yield ("id: %s\n" % seq) + "data: " + data.replace("\n", " ") + "\n\n"
					seq += 1
			return Response(stream(), mimetype="text/event-stream")	

		# Define a Jinja2 macro which generates Javascript code to load Hotwire Turbo
		# and connect it to the event source route /turbo-sse defined above.
		def turbo():
			url = "https://cdn.jsdelivr.net/npm/@hotwired/turbo@7.2.2/dist/turbo.es2017-umd.js"
			return Markup('''
				<script src="{url}"></script>
				<script>
					let events = new EventSource("/turbo-sse");
					events.addEventListener("open", (e) => console.log("SSE open"));
					events.addEventListener("error", (e) => console.log("SSE error:", e));
					events.addEventListener("message", (e) => console.log("SSE data:", e.lastEventId, e.data));
					Turbo.connectStreamSource(events);
					</script>
				''').format(url=url)
		app.context_processor(lambda: {'turbo': turbo})

	# Decorator which caller uses to provide a function which generates an ID number
	# for each SSE connection. We can then then send messages to that client by
	# using the same ID in the to= argument to push().
	def user_id(self, callback):
		self.user_id_callback = callback
		return callback

	def turbo_frame(self):
		"Is the current request from a Turbo-Frame?"
		return request.headers.get("Turbo-Frame")

	def can_stream(self):
		"Will the client accept a Turbo-Stream response?"
		return "text/vnd.turbo-stream.html" in request.accept_mimetypes

	def can_push(self, to=None):
		"Has the client connected an EventSource to receive a Turbo-Stream?"
		return to in self.clients

	def stream(self, stream):
		"Create a Turbo-Stream response"
		return Response(stream, mimetype="text/vnd.turbo-stream.html")

	def push(self, message, to=None):
		"Queue a Turbo Stream message for delivery to a client"
		logger.debug("Push message: %s %s", to, message)
		for client in self.clients.keys() if to is None else [to]:
			try:
				self.clients[client].put_nowait(message)
			except queue.Full:
				logger.info("EventStream client %s disconnected" % client)
				del self.clients[client]

