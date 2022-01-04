from werkzeug.serving import WSGIRequestHandler
import logging

logger = logging.getLogger("app.werkzeug")

# Remove escape codes and date from Werkzeug log lines
class MyWSGIRequestHandler(WSGIRequestHandler):
	logger = None
	def log_request(self, code="-", size="-"):
		msg = self.requestline
		self.log("info", '"%s" %s %s', msg, code, size)
	def log(self, type, message, *args):
		getattr(logger, type)(message, *args)

