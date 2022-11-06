#! /usr/bin/python3
# PyWebview documentation
# https://github.com/r0x0r/pywebview

import webview
from threading import Thread
from werkzeug.serving import make_server
from urllib.request import urlopen

from app.werkzeug_logging import MyWSGIRequestHandler
from app import app, socketio

def server():
	socketio.run(app, host="0.0.0.0", port=5000)

#server = make_server(host="127.0.0.1", port=5000, app=app, request_handler=MyWSGIRequestHandler)
#server_thread = Thread(target=server.serve_forever)
server_thread = Thread(target=server)
server_thread.daemon = True
server_thread.start()

webview.create_window(
	title='JW-Pubs: OBS',
	url='http://localhost:5000/obs/',
	width=1024,
	height=1024,
	)
webview.start()
print("Webview has exited.")

print("Shutting down server...")
try:
	urlopen('http://127.0.0.1:5000/obs/shutdown')
except Exception as e:
	pass
server_thread.join()
print("Server has stopt.")
