# A simple OBS Websocket client library

import websocket
import json
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)

class ObsEventReader:
	def __init__(self, hostname="localhost", port=4444, password="secret"):
		logger.debug("Connecting to OBS...")
		self.ws = websocket.WebSocket()
		self.ws.connect("ws://%s:%d" % (hostname, port))
		self.id = 1

		logger.debug("Logging in...")
		response = self.request({"request-type": "GetAuthRequired"})
		assert response['status'] == 'ok', response

		if response.get('authRequired'):
			secret = base64.b64encode(hashlib.sha256((password + response['salt']).encode('utf-8')).digest())
			auth = base64.b64encode(hashlib.sha256(secret + response['challenge'].encode('utf-8')).digest()).decode('utf-8')
			response = self.request({"request-type": "Authenticate", "auth": auth})
			assert response['status'] == 'ok', response

		logger.debug("Ready to receive messages from OBS.")

	def send_message(self, data):
		id = self.id
		self.id += 1
		data["message-id"] = str(id)
		self.ws.send(json.dumps(data))
		return id

	def recv_message(self):
		return json.loads(self.ws.recv())

	def request(self, data):
		id = self.send_message(data)
		response = self.recv_message()
		assert response['message-id'] == str(id)
		return response
