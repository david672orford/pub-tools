import logging
from werkzeug.serving import WSGIRequestHandler

# Simplify log messages coming from the Werkzeig HTTP server
class CleanlogWSGIRequestHandler(WSGIRequestHandler):
	logger = logging.getLogger("app.werkzeug")
	def log_request(self, code="-", size="-"):
		msg = self.requestline
		self.log("info", '"%s" %s %s', msg, code, size)
	def log(self, type, message, *args):
		getattr(self.logger, type)(message, *args)

